#!/usr/bin/env python3
"""Lint every JSON Schema under ``schemas/``.

Each schema is parsed as JSON, then ``Draft202012Validator.check_schema`` is
invoked to ensure the schema itself is well-formed. We also check that each
schema declares ``$schema``, ``$id``, ``title``, and ``description``.

Exits non-zero on any failure. Run from the repo root.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"

REQUIRED_TOP_KEYS = ("$schema", "$id", "title", "description")


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    fail = 0
    schema_files = sorted(SCHEMAS_DIR.glob("*.schema.json"))
    if not schema_files:
        print("WARNING: no *.schema.json files found")
        return 0

    for path in schema_files:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL  {path.relative_to(ROOT)}: invalid JSON: {exc}")
            fail += 1
            continue

        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            print(f"FAIL  {path.relative_to(ROOT)}: invalid schema: {exc}")
            fail += 1
            continue

        missing = [k for k in REQUIRED_TOP_KEYS if k not in schema]
        if missing:
            print(f"FAIL  {path.relative_to(ROOT)}: missing top-level keys: {missing}")
            fail += 1
            continue

        print(f"OK    {path.relative_to(ROOT)}")

    if fail:
        print(f"\nlint_schemas: {fail} schema(s) failed")
        return 1
    print(f"\nlint_schemas: all {len(schema_files)} schema(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
