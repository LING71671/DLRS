"""Knowledge-graph (entity + co-mention edge) extraction pipeline.

Inputs (in priority order, picked by ``_first_source_in_record``):

- ``derived/memory_atoms/<stem>.atoms.jsonl`` (preferred). The pipeline
  treats each atom's ``text`` as one **context unit** for edge emission:
  any two entity mentions that fall inside the same atom become a
  ``dlrs.co_mentioned_in`` edge candidate.
- ``derived/text/<stem>.clean.txt`` (fallback). Treated as one big block
  split into context units on blank lines.

Outputs (under ``<record>/derived/knowledge_graph/``):

- ``<stem>.nodes.jsonl`` — one node per line, conforms to
  ``schemas/entity-graph-node.schema.json``.
- ``<stem>.edges.jsonl`` — one edge per line, conforms to
  ``schemas/entity-graph-edge.schema.json``.
- ``<stem>.graph.descriptor.json`` — provenance descriptor conforming to
  ``schemas/derived-asset.schema.json``.

Backend (v0.6 first cut):

- ``regex`` (default, deterministic, dependency-free): extracts
  capitalised proper-noun-ish phrases via :mod:`re`, filters out
  redaction placeholders and common sentence-start tokens, dedupes by
  case-insensitive label. Within each context unit, consecutive
  mentions become a ``dlrs.co_mentioned_in`` edge with
  ``confidence=0.5``.

A full NER backend (e.g. spaCy ``en_core_web_sm``) would require a
network model download and so violates the v0.5 offline-first invariant
that v0.6 inherits. It is intentionally deferred until a vendored or
locally-cached model story is in place; the SPEC only advertises the
``regex`` backend so ``--backend spacy`` cannot accidentally be
selected today.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pipelines import PipelineSpec
from pipelines._descriptor import (
    DescriptorBuilder,
    sha256_of_bytes,
    validate_descriptor,
    write_json,
)
from pipelines._audit_bridge import maybe_bridge

PIPELINE_VERSION = "0.6.0"

ROOT = Path(__file__).resolve().parents[2]
DERIVED_SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"
NODE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-node.schema.json"
EDGE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-edge.schema.json"

VALID_SENSITIVITIES = (
    "S0_PUBLIC",
    "S1_INTERNAL",
    "S2_SENSITIVE",
    "S2_CONFIDENTIAL",
    "S3_BIOMETRIC",
    "S4_RESTRICTED",
    "S4_IDENTITY",
)


def _register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--record", required=False, help="Path to the record directory.")
    parser.add_argument(
        "--input",
        required=False,
        help="Path to a *.atoms.jsonl, *.clean.txt or .txt source. "
             "May be record-relative when --record is set.",
    )
    parser.add_argument(
        "--backend",
        choices=["regex"],
        default="regex",
        help="Extraction backend. Only 'regex' (deterministic, offline) is "
             "available in v0.6; an NER backend is deferred until a "
             "vendored / locally-cached model story is in place.",
    )
    parser.add_argument(
        "--sensitivity",
        choices=VALID_SENSITIVITIES,
        default="S2_SENSITIVE",
        help="Sensitivity tier copied onto every emitted node and edge. "
             "Defaults to S2_SENSITIVE (conservative). Wire-through from the "
             "source artefact's manifest sensitivity is the descriptor->audit "
             "bridge's job (#58).",
    )
    parser.add_argument(
        "--min-mentions",
        type=int,
        default=1,
        help="Drop any candidate entity that occurs strictly fewer times than "
             "this threshold across the input. Default: 1 (keep everything).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/knowledge_graph/.",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip the descriptor->audit/events.jsonl bridge (#58). Useful "
             "for fixture generation. The bridge is also a no-op when the "
             "record root has no manifest.json.",
    )


def _resolve_input(args: argparse.Namespace) -> tuple[Optional[Path], Path, str]:
    record_root: Optional[Path] = Path(args.record).resolve() if args.record else None

    if args.input:
        candidate = Path(args.input)
        if record_root is not None and not candidate.is_absolute():
            input_path = (record_root / args.input).resolve()
        else:
            input_path = candidate.resolve()
    else:
        if record_root is None:
            raise SystemExit("[knowledge_graph] one of --input or --record is required")
        input_path = _first_source_in_record(record_root)

    if not input_path.exists():
        raise SystemExit(f"[knowledge_graph] input not found: {input_path}")

    if record_root is not None:
        try:
            pointer_rel = str(input_path.relative_to(record_root))
        except ValueError:
            pointer_rel = input_path.name
    else:
        pointer_rel = input_path.name
    return record_root, input_path, pointer_rel


def _first_source_in_record(record_root: Path) -> Path:
    """Prefer an atoms.jsonl from #56; fall back to a clean.txt; then raw."""
    derived_atoms = record_root / "derived" / "memory_atoms"
    if derived_atoms.is_dir():
        atoms = sorted(derived_atoms.glob("*.atoms.jsonl"))
        if atoms:
            return atoms[0]

    derived_text = record_root / "derived" / "text"
    if derived_text.is_dir():
        cleaned = sorted(derived_text.glob("*.clean.txt"))
        if cleaned:
            return cleaned[0]

    for ext in (".txt", ".md"):
        candidates = sorted((record_root / "artifacts").rglob(f"*{ext}"))
        if candidates:
            return candidates[0]

    raise SystemExit(f"[knowledge_graph] no atoms.jsonl, clean.txt or raw text found under {record_root}")


def _read_record_id(record_root: Optional[Path], default: str) -> str:
    if record_root is None:
        return default
    manifest = record_root / "manifest.json"
    if not manifest.exists():
        return default
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("record_id", default)
    except (OSError, json.JSONDecodeError):
        return default


def _load_context_units(input_path: Path) -> list[str]:
    """Return the input as a list of context units (one per atom / paragraph).

    - ``*.atoms.jsonl`` → one unit per atom's ``text`` field.
    - Anything else → split on blank lines (paragraphs).
    """
    name = input_path.name
    if name.endswith(".atoms.jsonl"):
        units: list[str] = []
        for line in input_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                atom = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = atom.get("text")
            if isinstance(text, str) and text.strip():
                units.append(text)
        return units

    raw = input_path.read_text(encoding="utf-8")
    return [chunk.strip() for chunk in raw.split("\n\n") if chunk.strip()]


def _stem_for(input_path: Path) -> str:
    """Strip known double-suffixes."""
    name = input_path.name
    for suffix in (".atoms.jsonl", ".clean.txt", ".transcript.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return input_path.stem


def _run(args: argparse.Namespace) -> int:
    from pipelines.knowledge_graph.extract import extract_regex_graph

    record_root, input_path, pointer_rel = _resolve_input(args)

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "knowledge_graph"
    else:
        out_dir = input_path.parent / "derived" / "knowledge_graph"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _stem_for(input_path)
    nodes_path = out_dir / f"{stem}.nodes.jsonl"
    edges_path = out_dir / f"{stem}.edges.jsonl"
    descriptor_path = out_dir / f"{stem}.graph.descriptor.json"

    units = _load_context_units(input_path)
    record_id = _read_record_id(record_root, default="dlrs_unknown")

    nodes, edges = extract_regex_graph(
        context_units=units,
        record_id=record_id,
        evidence_pointer=pointer_rel,
        sensitivity=args.sensitivity,
        min_mentions=args.min_mentions,
        pipeline_version=PIPELINE_VERSION,
    )

    _validate_against(nodes, NODE_SCHEMA_PATH, "node")
    _validate_against(edges, EDGE_SCHEMA_PATH, "edge")

    nodes_blob = "".join(json.dumps(n, ensure_ascii=False) + "\n" for n in nodes)
    edges_blob = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in edges)
    nodes_path.write_text(nodes_blob, encoding="utf-8")
    edges_path.write_text(edges_blob, encoding="utf-8")

    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="knowledge_graph",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "backend": args.backend,
            "sensitivity": args.sensitivity,
            "min_mentions": args.min_mentions,
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    )
    builder.add_input(source_pointer=pointer_rel, file_path=input_path)
    builder.extra_metadata["node_count"] = len(nodes)
    builder.extra_metadata["edge_count"] = len(edges)
    builder.extra_metadata["nodes_hash"] = sha256_of_bytes(nodes_blob.encode("utf-8"))
    builder.extra_metadata["edges_hash"] = sha256_of_bytes(edges_blob.encode("utf-8"))

    if record_root is not None:
        try:
            out_path_in_record = str(nodes_path.relative_to(record_root))
        except ValueError:
            out_path_in_record = f"derived/knowledge_graph/{nodes_path.name}"
    else:
        out_path_in_record = f"derived/knowledge_graph/{nodes_path.name}"

    descriptor = builder.finalise(out_path_in_record, nodes_path)
    validate_descriptor(descriptor, DERIVED_SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    audit_ref = maybe_bridge(
        record_root=record_root,
        pipeline_name="knowledge_graph",
        descriptor=descriptor,
        descriptor_path=descriptor_path,
        skip=getattr(args, "no_audit", False),
    )
    if audit_ref:
        print(f"[knowledge_graph] audit_event_ref={audit_ref}", file=sys.stderr)

    print(f"[knowledge_graph] backend={args.backend} input={input_path}", file=sys.stderr)
    print(
        f"[knowledge_graph] wrote {nodes_path} ({len(nodes)} node(s)), "
        f"{edges_path} ({len(edges)} edge(s))",
        file=sys.stderr,
    )
    print(f"[knowledge_graph] wrote {descriptor_path}", file=sys.stderr)
    return 0


def _validate_against(items: list[dict], schema_path: Path, kind: str) -> None:
    """Validate every emitted node / edge against its schema."""
    from jsonschema import Draft202012Validator  # type: ignore

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    bad: list[str] = []
    for i, item in enumerate(items):
        errors = sorted(validator.iter_errors(item), key=lambda e: e.path)
        if errors:
            msg = "; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors[:3])
            ident = item.get(f"{kind}_id", "?")
            bad.append(f"{kind}[{i}] (id={ident}): {msg}")
    if bad:
        raise ValueError(
            f"{kind} schema validation failed for {len(bad)} item(s):\n  - "
            + "\n  - ".join(bad)
        )


SPEC = PipelineSpec(
    name="knowledge_graph",
    description="Extract entity-graph nodes + co-mention edges from atoms or cleaned text (regex; deterministic; offline).",
    inputs=["atoms.jsonl", "clean.txt", "text/plain"],
    outputs=["nodes.jsonl", "edges.jsonl", "graph.descriptor.json"],
    dependencies=["jsonschema>=4.20"],
    output_pointer_template="derived/knowledge_graph/{stem}.nodes.jsonl",
    register=_register,
    run=_run,
)
