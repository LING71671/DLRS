#!/usr/bin/env python3
"""Sanity tests for ``schemas/memory-atom.schema.json``.

Mirrors the structure of ``test_derived_asset_schema.py``: construct a known-
good atom, then mutate it to provoke each schema-level rejection. The
pipelines/memory_atoms/ implementation (issue #56) will use the same schema
to validate every atom it emits, so these cases double as pre-flight checks
for that pipeline.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "memory-atom.schema.json"


def _good_atom() -> dict:
    return {
        "schema_version": "dlrs-memory-atom/1.0",
        "atom_id": "01HW91QJTR4ETRBM3DNJK4Y9MA",
        "record_id": "dlrs_94f1c9b8_lin-example",
        "source_pointer": "derived/text/diary_2026-04-01.clean.txt",
        "text": "在 2026 年 4 月，作者搬到上海，开始一段新的研究项目。",
        "confidence": 0.6,
        "sensitivity": "S1_INTERNAL",
        "erasable": True,
        "redaction_safe": True,
        "created_at": "2026-04-26T08:00:00Z",
        "pipeline_version": "0.6.0",
    }


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    cases: list[tuple[str, dict, bool]] = []  # (name, atom, expect_valid)

    cases.append(("good atom", _good_atom(), True))

    # Optional fields populated -> still valid.
    full = _good_atom()
    full["expires_at"] = "2027-04-26T08:00:00Z"
    full["audit_event_ref"] = "audit/events.jsonl#L142"
    cases.append(("good atom with optional fields", full, True))

    # `redaction_safe = false` -> reject (the contract is the field itself).
    not_safe = _good_atom()
    not_safe["redaction_safe"] = False
    cases.append(("redaction_safe=false", not_safe, False))

    # Missing redaction_safe entirely -> reject.
    missing_safe = _good_atom()
    missing_safe.pop("redaction_safe")
    cases.append(("missing redaction_safe", missing_safe, False))

    # confidence > 1 -> reject.
    over_conf = _good_atom()
    over_conf["confidence"] = 1.5
    cases.append(("confidence > 1", over_conf, False))

    # confidence < 0 -> reject.
    neg_conf = _good_atom()
    neg_conf["confidence"] = -0.1
    cases.append(("confidence < 0", neg_conf, False))

    # record_id pattern violation -> reject (must start with dlrs_).
    bad_record = _good_atom()
    bad_record["record_id"] = "94f1c9b8_lin-example"
    cases.append(("record_id missing dlrs_ prefix", bad_record, False))

    # absolute source_pointer -> reject.
    abs_pointer = _good_atom()
    abs_pointer["source_pointer"] = "/tmp/diary.txt"
    cases.append(("absolute source_pointer", abs_pointer, False))

    # external URL source_pointer -> reject.
    url_pointer = _good_atom()
    url_pointer["source_pointer"] = "https://example.org/diary.txt"
    cases.append(("https source_pointer", url_pointer, False))

    # s3 source_pointer -> reject (atoms are derived; original storage stays opaque).
    s3_pointer = _good_atom()
    s3_pointer["source_pointer"] = "s3://bucket/diary.txt"
    cases.append(("s3 source_pointer", s3_pointer, False))

    # text empty -> reject.
    empty_text = _good_atom()
    empty_text["text"] = ""
    cases.append(("empty text", empty_text, False))

    # text too long -> reject.
    too_long = _good_atom()
    too_long["text"] = "x" * 5000
    cases.append(("text > 4096 chars", too_long, False))

    # sensitivity outside enum -> reject.
    bad_sens = _good_atom()
    bad_sens["sensitivity"] = "S5_TOPSECRET"
    cases.append(("sensitivity outside enum", bad_sens, False))

    # additionalProperties at top level -> reject.
    extra = _good_atom()
    extra["random_extra"] = 1
    cases.append(("unknown top-level field", extra, False))

    # schema_version not the constant -> reject.
    wrong_version = _good_atom()
    wrong_version["schema_version"] = "dlrs-memory-atom/1.1"
    cases.append(("wrong schema_version", wrong_version, False))

    # pipeline_version pattern violation -> reject.
    bad_pv = _good_atom()
    bad_pv["pipeline_version"] = "v0.6"  # missing patch component
    cases.append(("pipeline_version not semver", bad_pv, False))

    # bad audit_event_ref shape -> reject.
    bad_ref = _good_atom()
    bad_ref["audit_event_ref"] = "audit/events.jsonl:142"  # wrong separator
    cases.append(("audit_event_ref wrong separator", bad_ref, False))

    failures = 0
    for name, doc, expect_valid in cases:
        errors = list(validator.iter_errors(doc))
        is_valid = not errors
        if is_valid != expect_valid:
            failures += 1
            print(f"FAIL  {name}: expected valid={expect_valid} got valid={is_valid}")
            for e in errors[:3]:
                print(f"      - {e.message}")
        else:
            print(f"OK    {name}")

    if failures:
        print(f"\ntest_memory_atom_schema: {failures}/{len(cases)} case(s) failed")
        return 1
    print(f"\ntest_memory_atom_schema: all {len(cases)} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
