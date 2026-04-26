#!/usr/bin/env python3
"""Validate every example archive under ``examples/`` against the manifest schema.

Each subdirectory of ``examples/`` MUST contain a ``manifest.json``. We run
``tools/validate_manifest.py`` against each one. We also validate
``public_profile.json`` against the public-profile schema when present.

Run from the repo root. Non-zero exit on failures.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCHEMAS = ROOT / "schemas"


def _load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_public_profile(path: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed; run pip install -r tools/requirements.txt"]
    schema = _load_json(SCHEMAS / "public-profile.schema.json")
    instance = _load_json(path)
    validator = Draft202012Validator(schema)
    errors = []
    for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(map(str, e.path)) or "<root>"
        errors.append(f"{loc}: {e.message}")
    return errors


def main() -> int:
    if not EXAMPLES.exists():
        print("validate_examples: examples/ directory not found")
        return 0

    fail = 0
    examples = sorted([p for p in EXAMPLES.iterdir() if p.is_dir()])
    for ex in examples:
        manifest = ex / "manifest.json"
        if not manifest.exists():
            print(f"FAIL  {ex.relative_to(ROOT)}: missing manifest.json")
            fail += 1
            continue
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_manifest.py"), str(manifest)],
            text=True, capture_output=True,
        )
        if r.returncode != 0:
            print(f"FAIL  {ex.relative_to(ROOT)}/manifest.json")
            for line in (r.stdout + r.stderr).strip().splitlines():
                print(f"  {line}")
            fail += 1
        else:
            print(f"OK    {ex.relative_to(ROOT)}/manifest.json")

        public_profile = ex / "public_profile.json"
        if public_profile.exists():
            errs = _validate_public_profile(public_profile)
            if errs:
                print(f"FAIL  {public_profile.relative_to(ROOT)}")
                for e in errs:
                    print(f"  - {e}")
                fail += 1
            else:
                print(f"OK    {public_profile.relative_to(ROOT)}")

    if fail:
        print(f"\nvalidate_examples: {fail} example(s) failed")
        return 1
    print(f"\nvalidate_examples: all {len(examples)} example(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
