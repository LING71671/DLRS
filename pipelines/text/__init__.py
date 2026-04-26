"""Text cleaning + sensitive-info redaction pipeline.

Inputs:

- ``text/plain`` files (``.txt``, ``.md``).
- ASR transcripts produced by :mod:`pipelines.asr`. The pipeline reads
  ``segments[].text`` and concatenates them with newlines.

Outputs (next to each input under ``<record>/derived/text/``):

- ``<stem>.clean.txt`` — normalised + redacted text.
- ``<stem>.redactions.json`` — list of ``{kind, start, end, replacement}``
  triples. Never carries the original sensitive substring.
- ``<stem>.clean.descriptor.json`` — provenance descriptor conforming to
  ``schemas/derived-asset.schema.json``.
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
    validate_descriptor,
    write_json,
)

PIPELINE_VERSION = "0.5.0"

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--record", required=False, help="Path to the record directory.")
    parser.add_argument(
        "--input",
        required=False,
        help="Path to a text or transcript.json file. May be record-relative when --record is set.",
    )
    parser.add_argument(
        "--mode",
        choices=["normalize", "redact", "both"],
        default="both",
        help="What to run: 'normalize' (NFKC+whitespace), 'redact' (sensitive info), or 'both'.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/text/.",
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
            raise SystemExit("[text] one of --input or --record is required")
        input_path = _first_text_in_record(record_root)

    if not input_path.exists():
        raise SystemExit(f"[text] input not found: {input_path}")

    if record_root is not None:
        try:
            pointer_rel = str(input_path.relative_to(record_root))
        except ValueError:
            pointer_rel = input_path.name
    else:
        pointer_rel = input_path.name
    return record_root, input_path, pointer_rel


def _first_text_in_record(record_root: Path) -> Path:
    """Prefer a transcript produced by ``pipelines.asr``; fall back to any txt."""
    derived_asr = record_root / "derived" / "asr"
    if derived_asr.is_dir():
        transcripts = sorted(derived_asr.glob("*.transcript.json"))
        if transcripts:
            return transcripts[0]

    for ext in (".txt", ".md"):
        candidates = sorted((record_root / "artifacts").rglob(f"*{ext}"))
        if candidates:
            return candidates[0]

    raise SystemExit(f"[text] no text or transcript found under {record_root}")


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
    """Load raw text from a plain file or a transcript.json produced by ASR."""
    if input_path.suffix.lower() == ".json":
        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"[text] {input_path} is not valid JSON: {exc}")
        segments = data.get("segments")
        if isinstance(segments, list):
            return "\n".join(seg.get("text", "") for seg in segments).strip()
        # Fallback: dump the whole JSON as a string so the pipeline still
        # produces an artefact rather than failing for unknown JSON shapes.
        return json.dumps(data, ensure_ascii=False)
    return input_path.read_text(encoding="utf-8")


def _stem_for(input_path: Path) -> str:
    """Strip the longest known double-suffix so 'foo.transcript.json' → 'foo'."""
    name = input_path.name
    for suffix in (".transcript.json",):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return input_path.stem


def _run(args: argparse.Namespace) -> int:
    from pipelines.text.cleaning import clean

    record_root, input_path, pointer_rel = _resolve_input(args)

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "text"
    else:
        out_dir = input_path.parent / "derived" / "text"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _stem_for(input_path)
    clean_path = out_dir / f"{stem}.clean.txt"
    redactions_path = out_dir / f"{stem}.redactions.json"
    descriptor_path = out_dir / f"{stem}.clean.descriptor.json"

    raw = _load_text(input_path)
    cleaned, redactions = clean(
        raw,
        do_normalise=args.mode in ("normalize", "both"),
        do_redact=args.mode in ("redact", "both"),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    clean_path.write_text(cleaned + ("\n" if not cleaned.endswith("\n") else ""), encoding="utf-8")
    write_json(
        redactions_path,
        {
            "schema": "dlrs-text-redactions/1.0",
            "redactions": [r.to_dict() for r in redactions],
            "summary": _redaction_summary(redactions),
        },
    )

    record_id = _read_record_id(record_root, default="dlrs_unknown")
    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="text",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "mode": args.mode,
            "normaliser_version": "1.0",
            "redactor_version": "1.0",
        },
    )
    builder.add_input(source_pointer=pointer_rel, file_path=input_path)
    builder.extra_metadata["redaction_summary"] = _redaction_summary(redactions)

    if record_root is not None:
        try:
            out_path_in_record = str(clean_path.relative_to(record_root))
        except ValueError:
            out_path_in_record = f"derived/text/{clean_path.name}"
    else:
        out_path_in_record = f"derived/text/{clean_path.name}"

    descriptor = builder.finalise(out_path_in_record, clean_path)
    validate_descriptor(descriptor, SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    print(f"[text] mode={args.mode} input={input_path}", file=sys.stderr)
    print(
        f"[text] wrote {clean_path} ({clean_path.stat().st_size} bytes), "
        f"{len(redactions)} redaction(s)",
        file=sys.stderr,
    )
    print(f"[text] wrote {descriptor_path}", file=sys.stderr)
    return 0


def _redaction_summary(redactions: list) -> dict:
    counts: dict[str, int] = {}
    for r in redactions:
        counts[r.kind] = counts.get(r.kind, 0) + 1
    return {"total": len(redactions), "by_kind": counts}


SPEC = PipelineSpec(
    name="text",
    description="Deterministic text normalisation and conservative sensitive-info redaction (offline).",
    inputs=["text/plain", "transcript.json"],
    outputs=["clean.txt", "redactions.json", "clean.descriptor.json"],
    dependencies=["jsonschema>=4.20"],
    output_pointer_template="derived/text/{stem}.clean.txt",
    register=_register,
    run=_run,
)
