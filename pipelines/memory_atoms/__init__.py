"""Memory-atom extraction pipeline.

Inputs (in order of preference, picked by ``_first_text_in_record``):

- ``derived/text/<stem>.clean.txt`` — the redacted output of
  :mod:`pipelines.text`. The atom emitter inherits its redaction guarantee
  from this layer, which is why the atom schema's ``redaction_safe`` field
  is a const ``true``: by the time text reaches this pipeline, the v0.5
  redaction pass has already substituted every PII match for its category
  placeholder (``<EMAIL>``, ``<PHONE_CN>`` …).
- ``artifacts/**/*.txt`` / ``*.md`` — fallback when no cleaned derivative
  is available. The atom emitter still re-runs the v0.5 redactor on this
  input before emitting atoms, so raw text is acceptable.

Outputs (under ``<record>/derived/memory_atoms/``):

- ``<stem>.atoms.jsonl`` — one atom per line, each line a JSON document
  conforming to ``schemas/memory-atom.schema.json``.
- ``<stem>.atoms.descriptor.json`` — provenance descriptor conforming to
  ``schemas/derived-asset.schema.json``.

Backends:

- ``paragraph`` (default, deterministic, no third-party deps): splits the
  cleaned text on blank lines and emits one atom per non-empty paragraph.
  Pipeline confidence is pinned to ``0.6`` so consumers can detect the
  baseline backend without inspecting ``model``.
- ``spacy`` (opt-in, lazy import): sentence segmentation via spaCy's
  language-agnostic ``sentencizer``. Each sentence becomes one atom.
  spaCy is imported only when this backend is selected, so machines
  without it can still run ``--help`` and the default backend.

The pipeline NEVER attempts to fetch remote models or call hosted APIs.
The offline-first invariant enforced by ``tools/validate_pipelines.py``
applies here just like the v0.5 pipelines.
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
    ModelInfo,
    sha256_of_bytes,
    validate_descriptor,
    write_json,
)
from pipelines._audit_bridge import maybe_bridge

PIPELINE_VERSION = "0.6.0"

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"
ATOM_SCHEMA_PATH = ROOT / "schemas" / "memory-atom.schema.json"

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
        help="Path to a clean.txt / transcript.json / .txt / .md file. "
             "May be record-relative when --record is set.",
    )
    parser.add_argument(
        "--backend",
        choices=["paragraph", "spacy"],
        default="paragraph",
        help="Extraction backend. 'paragraph' (default) is dependency-free; "
             "'spacy' opt-in performs sentence segmentation.",
    )
    parser.add_argument(
        "--sensitivity",
        choices=VALID_SENSITIVITIES,
        default="S2_SENSITIVE",
        help="Sensitivity tier copied onto every emitted atom. Defaults to "
             "S2_SENSITIVE (conservative). Wire-through from the source "
             "artefact's manifest sensitivity is the descriptor->audit bridge's "
             "job (#58).",
    )
    parser.add_argument(
        "--erasable",
        choices=["true", "false"],
        default="true",
        help="Whether emitted atoms can be deleted on consent withdrawal. "
             "Default true. Set to false when the atoms feed a knowledge "
             "graph whose erasure would leave dangling edges.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/memory_atoms/.",
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
            raise SystemExit("[memory_atoms] one of --input or --record is required")
        input_path = _first_text_in_record(record_root)

    if not input_path.exists():
        raise SystemExit(f"[memory_atoms] input not found: {input_path}")

    if record_root is not None:
        try:
            pointer_rel = str(input_path.relative_to(record_root))
        except ValueError:
            pointer_rel = input_path.name
    else:
        pointer_rel = input_path.name
    return record_root, input_path, pointer_rel


def _first_text_in_record(record_root: Path) -> Path:
    """Prefer the cleaned text from ``pipelines.text``; fall back to raw."""
    derived_text = record_root / "derived" / "text"
    if derived_text.is_dir():
        cleaned = sorted(derived_text.glob("*.clean.txt"))
        if cleaned:
            return cleaned[0]

    derived_asr = record_root / "derived" / "asr"
    if derived_asr.is_dir():
        transcripts = sorted(derived_asr.glob("*.transcript.json"))
        if transcripts:
            return transcripts[0]

    for ext in (".txt", ".md"):
        candidates = sorted((record_root / "artifacts").rglob(f"*{ext}"))
        if candidates:
            return candidates[0]

    raise SystemExit(f"[memory_atoms] no text or transcript found under {record_root}")


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


def _load_text(input_path: Path) -> str:
    """Load raw text from a plain file, .clean.txt, or transcript JSON."""
    if input_path.suffix.lower() == ".json":
        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"[memory_atoms] {input_path} is not valid JSON: {exc}")
        segments = data.get("segments")
        if isinstance(segments, list):
            return "\n".join(seg.get("text", "") for seg in segments).strip()
        return json.dumps(data, ensure_ascii=False)
    return input_path.read_text(encoding="utf-8")


def _stem_for(input_path: Path) -> str:
    """Strip known double-suffixes so 'foo.clean.txt' or 'foo.transcript.json' → 'foo'."""
    name = input_path.name
    for suffix in (".clean.txt", ".transcript.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return input_path.stem


def _ensure_redacted(text: str) -> str:
    """Re-run the v0.5 redactor on the input text.

    A no-op when the input is already a ``derived/text/<stem>.clean.txt``;
    a real defensive pass when the input is a raw ``.txt`` / ``.md``.
    Either way the atom emitter holds the contract: every atom's text has
    been through the v0.5 redaction pass at least once.
    """
    from pipelines.text.cleaning import clean

    cleaned, _redactions = clean(text, do_normalise=False, do_redact=True)
    return cleaned


def _run(args: argparse.Namespace) -> int:
    from pipelines.memory_atoms.extract import (
        extract_paragraph_atoms,
        extract_spacy_atoms,
    )

    record_root, input_path, pointer_rel = _resolve_input(args)

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "memory_atoms"
    else:
        out_dir = input_path.parent / "derived" / "memory_atoms"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _stem_for(input_path)
    atoms_path = out_dir / f"{stem}.atoms.jsonl"
    descriptor_path = out_dir / f"{stem}.atoms.descriptor.json"

    raw = _load_text(input_path)
    redacted = _ensure_redacted(raw)

    record_id = _read_record_id(record_root, default="dlrs_unknown")
    erasable = args.erasable == "true"

    if args.backend == "spacy":
        atoms = extract_spacy_atoms(
            text=redacted,
            record_id=record_id,
            source_pointer=pointer_rel,
            sensitivity=args.sensitivity,
            erasable=erasable,
            pipeline_version=PIPELINE_VERSION,
        )
        model_info = ModelInfo(
            id="spacy:blank-sentencizer",
            version="lazy",
            source="local",
            online_api_used=False,
        )
        atom_backend = "spacy"
    else:
        atoms = extract_paragraph_atoms(
            text=redacted,
            record_id=record_id,
            source_pointer=pointer_rel,
            sensitivity=args.sensitivity,
            erasable=erasable,
            pipeline_version=PIPELINE_VERSION,
        )
        model_info = None
        atom_backend = "paragraph"

    _validate_atoms(atoms)

    payload = "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in atoms)
    atoms_path.write_text(payload, encoding="utf-8")

    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="memory_atoms",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "backend": atom_backend,
            "sensitivity": args.sensitivity,
            "erasable": erasable,
            "atom_count": len(atoms),
        },
        model=model_info,
    )
    builder.add_input(source_pointer=pointer_rel, file_path=input_path)
    builder.extra_metadata["atom_count"] = len(atoms)
    builder.extra_metadata["atom_text_hash"] = sha256_of_bytes(payload.encode("utf-8"))

    if record_root is not None:
        try:
            out_path_in_record = str(atoms_path.relative_to(record_root))
        except ValueError:
            out_path_in_record = f"derived/memory_atoms/{atoms_path.name}"
    else:
        out_path_in_record = f"derived/memory_atoms/{atoms_path.name}"

    descriptor = builder.finalise(out_path_in_record, atoms_path)
    validate_descriptor(descriptor, SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    audit_ref = maybe_bridge(
        record_root=record_root,
        pipeline_name="memory_atoms",
        descriptor=descriptor,
        descriptor_path=descriptor_path,
        skip=getattr(args, "no_audit", False),
    )
    if audit_ref:
        print(f"[memory_atoms] audit_event_ref={audit_ref}", file=sys.stderr)

    print(f"[memory_atoms] backend={atom_backend} input={input_path}", file=sys.stderr)
    print(
        f"[memory_atoms] wrote {atoms_path} ({atoms_path.stat().st_size} bytes), "
        f"{len(atoms)} atom(s)",
        file=sys.stderr,
    )
    print(f"[memory_atoms] wrote {descriptor_path}", file=sys.stderr)
    return 0


def _validate_atoms(atoms: list[dict]) -> None:
    """Validate every emitted atom against ``schemas/memory-atom.schema.json``."""
    from jsonschema import Draft202012Validator  # type: ignore

    schema = json.loads(ATOM_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    bad: list[str] = []
    for i, atom in enumerate(atoms):
        errors = sorted(validator.iter_errors(atom), key=lambda e: e.path)
        if errors:
            msg = "; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors[:3])
            bad.append(f"atom[{i}] (id={atom.get('atom_id', '?')}): {msg}")
    if bad:
        raise ValueError(
            "memory-atom schema validation failed for {n} atom(s):\n  - {body}".format(
                n=len(bad), body="\n  - ".join(bad)
            )
        )


SPEC = PipelineSpec(
    name="memory_atoms",
    description="Extract long-term-memory atoms from cleaned text (paragraph default; spacy opt-in; offline).",
    inputs=["text/plain", "clean.txt", "transcript.json"],
    outputs=["atoms.jsonl", "atoms.descriptor.json"],
    dependencies=["jsonschema>=4.20"],
    output_pointer_template="derived/memory_atoms/{stem}.atoms.jsonl",
    register=_register,
    run=_run,
)
