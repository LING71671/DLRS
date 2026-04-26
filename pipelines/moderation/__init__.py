"""Content moderation pipeline.

Inputs:

- ``derived/text/<stem>.clean.txt`` produced by :mod:`pipelines.text`.
- Any plain text file via ``--input``.

Outputs (under ``<record>/derived/moderation/``):

- ``<stem>.moderation.json`` — list of flags (rule name, category,
  severity, char span). Never carries the matched substring.
- ``<stem>.moderation.descriptor.json`` — provenance descriptor with
  ``moderation_outcome`` set to ``pass`` / ``flag`` / ``block``.
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
        help="Path to a clean text file. Record-relative when --record is set.",
    )
    parser.add_argument(
        "--policy-file",
        default=None,
        help="Optional custom policy JSON/YAML appended to the built-in policy.",
    )
    parser.add_argument(
        "--no-builtin",
        action="store_true",
        help="Disable the built-in policy. Requires --policy-file.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/moderation/.",
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
            raise SystemExit("[moderation] one of --input or --record is required")
        input_path = _first_text_in_record(record_root)

    if not input_path.exists():
        raise SystemExit(f"[moderation] input not found: {input_path}")

    if record_root is not None:
        try:
            pointer_rel = str(input_path.relative_to(record_root))
        except ValueError:
            pointer_rel = input_path.name
    else:
        pointer_rel = input_path.name
    return record_root, input_path, pointer_rel


def _first_text_in_record(record_root: Path) -> Path:
    derived_text = record_root / "derived" / "text"
    if derived_text.is_dir():
        candidates = sorted(derived_text.glob("*.clean.txt"))
        if candidates:
            return candidates[0]
    raise SystemExit(
        f"[moderation] no derived/text/*.clean.txt found under {record_root}; "
        "run pipelines.text first or pass --input"
    )


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


def _stem_for(input_path: Path) -> str:
    name = input_path.name
    for suffix in (".clean.txt",):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return input_path.stem


def _run(args: argparse.Namespace) -> int:
    from pipelines.moderation.policies import outcome_for, select_policy

    record_root, input_path, pointer_rel = _resolve_input(args)

    policy = select_policy(
        use_builtin=not args.no_builtin,
        custom_path=Path(args.policy_file).resolve() if args.policy_file else None,
    )

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "moderation"
    else:
        out_dir = input_path.parent / "derived" / "moderation"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _stem_for(input_path)
    moderation_path = out_dir / f"{stem}.moderation.json"
    descriptor_path = out_dir / f"{stem}.moderation.descriptor.json"

    text = input_path.read_text(encoding="utf-8")
    flags = policy.scan(text)
    outcome = outcome_for(flags)
    summary = _summary(flags)

    write_json(
        moderation_path,
        {
            "schema": "dlrs-moderation/1.0",
            "policy": {"name": policy.name, "version": policy.version, "rule_count": len(policy.rules)},
            "outcome": outcome,
            "summary": summary,
            "flags": [f.to_dict() for f in flags],
        },
    )

    record_id = _read_record_id(record_root, default="dlrs_unknown")
    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="moderation",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "policy_name": policy.name,
            "policy_version": policy.version,
            "use_builtin": not args.no_builtin,
            "policy_file": str(args.policy_file) if args.policy_file else None,
        },
        moderation_outcome=outcome,
    )
    builder.add_input(source_pointer=pointer_rel, file_path=input_path)
    builder.extra_metadata["flag_count"] = len(flags)
    builder.extra_metadata["summary"] = summary

    if record_root is not None:
        try:
            out_path_in_record = str(moderation_path.relative_to(record_root))
        except ValueError:
            out_path_in_record = f"derived/moderation/{moderation_path.name}"
    else:
        out_path_in_record = f"derived/moderation/{moderation_path.name}"

    descriptor = builder.finalise(out_path_in_record, moderation_path)
    validate_descriptor(descriptor, SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    print(
        f"[moderation] policy={policy.name} flags={len(flags)} outcome={outcome}",
        file=sys.stderr,
    )
    print(f"[moderation] wrote {moderation_path}", file=sys.stderr)
    print(f"[moderation] wrote {descriptor_path}", file=sys.stderr)
    return 0


def _summary(flags) -> dict:
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for f in flags:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_category[f.category] = by_category.get(f.category, 0) + 1
    return {"total": len(flags), "by_severity": by_severity, "by_category": by_category}


SPEC = PipelineSpec(
    name="moderation",
    description="Deterministic content moderation: regex/wordlist policy → pass/flag/block (offline).",
    inputs=["text.clean.txt", "text/plain"],
    outputs=["moderation.json", "moderation.descriptor.json"],
    dependencies=["jsonschema>=4.20"],
    output_pointer_template="derived/moderation/{stem}.moderation.json",
    register=_register,
    run=_run,
)
