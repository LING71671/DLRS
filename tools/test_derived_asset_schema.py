#!/usr/bin/env python3
"""Sanity tests for ``schemas/derived-asset.schema.json``.

These tests do not exercise any pipeline body. They construct synthetic
descriptors and assert that the schema (a) accepts well-formed examples and
(b) rejects malformed ones. The pipeline implementations themselves
(issues #31-#34) will use the same schema to validate their actual outputs.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _good_descriptor() -> dict:
    return {
        "schema_version": "dlrs-derived-asset/1.0",
        "derived_id": "dlrs_derived_4f3e2a8c",
        "record_id": "dlrs_94f1c9b8_lin-example",
        "pipeline": "asr",
        "pipeline_version": "0.5.0",
        "created_at": "2026-04-26T06:30:00Z",
        "actor_role": "system",
        "inputs": {
            "source_pointers": [
                "artifacts/raw_pointers/audio/voice_master.pointer.json"
            ],
            "inputs_hash": "sha256:" + "a" * 64,
        },
        "model": {
            "id": "faster-whisper:small",
            "version": "rev:abcd1234",
            "source": "local-cache:~/.cache/huggingface",
            "online_api_used": False,
        },
        "parameters": {"language": "zh", "device": "cpu"},
        "output": {
            "path": "derived/asr/voice_master.transcript.json",
            "outputs_hash": "sha256:" + "b" * 64,
            "byte_size": 4096,
        },
    }


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    cases: list[tuple[str, dict, bool]] = []  # (name, descriptor, expect_valid)

    cases.append(("good asr descriptor", _good_descriptor(), True))

    # Moderation pipeline does not require model.*
    text_only = _good_descriptor()
    text_only["pipeline"] = "moderation"
    text_only["output"]["path"] = "derived/moderation/voice_master.report.json"
    text_only.pop("model")
    cases.append(("moderation without model", text_only, True))

    # ASR pipeline missing model -> reject
    asr_no_model = _good_descriptor()
    asr_no_model.pop("model")
    cases.append(("asr without model", asr_no_model, False))

    # Output path under wrong derived/<name>/ -> reject
    bad_path = _good_descriptor()
    bad_path["output"]["path"] = "derived/vector/voice_master.index.json"  # 'vector' is not a valid pipeline name
    cases.append(("output path with bad pipeline segment", bad_path, False))

    # online_api_used = true -> reject (offline-first invariant)
    online = _good_descriptor()
    online["model"]["online_api_used"] = True
    cases.append(("model.online_api_used=true", online, False))

    # Bad inputs_hash -> reject
    bad_hash = _good_descriptor()
    bad_hash["inputs"]["inputs_hash"] = "md5:" + "a" * 32
    cases.append(("non-sha256 inputs_hash", bad_hash, False))

    # additionalProperties at top level -> reject
    extra = _good_descriptor()
    extra["random_extra"] = 1
    cases.append(("unknown top-level field", extra, False))

    # schema_version not the constant -> reject
    wrong_version = _good_descriptor()
    wrong_version["schema_version"] = "dlrs-derived-asset/1.1"
    cases.append(("wrong schema_version", wrong_version, False))

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
        print(f"\ntest_derived_asset_schema: {failures}/{len(cases)} case(s) failed")
        return 1
    print(f"\ntest_derived_asset_schema: all {len(cases)} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
