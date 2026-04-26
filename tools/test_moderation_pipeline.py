#!/usr/bin/env python3
"""Tests for ``pipelines.moderation``.

Layers:

1. Unit tests for the rule engine: scan() returns flags with correct
   spans, severity-aggregation produces the right outcome, custom JSON
   policy loads and merges with the built-in.
2. End-to-end CLI test that runs ``run_pipeline.py moderation`` against
   a synthetic record and validates the descriptor against
   ``schemas/derived-asset.schema.json`` (including the
   ``moderation_outcome`` enum).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.moderation.policies import (  # noqa: E402
    Policy,
    Rule,
    builtin_policy,
    load_policy_file,
    merge_policies,
    outcome_for,
    select_policy,
)

SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _unit_tests_outcome(errors: list[str]) -> None:
    high = Rule.from_dict({"name": "h", "category": "x", "severity": "high", "patterns": ["foo"]})
    med = Rule.from_dict({"name": "m", "category": "x", "severity": "medium", "patterns": ["bar"]})
    low = Rule.from_dict({"name": "l", "category": "x", "severity": "low", "patterns": ["baz"]})

    p = Policy(name="t", version="t", rules=[high, med, low])

    cases = [
        ("hello world", "pass"),
        ("baz only", "pass"),
        ("bar baz", "flag"),
        ("foo", "block"),
        ("bar foo baz", "block"),
    ]
    for text, expected in cases:
        flags = p.scan(text)
        got = outcome_for(flags)
        _assert(
            got == expected,
            f"outcome[{text!r}] expected {expected!r}, got {got!r} (flags={[f.rule_name for f in flags]})",
            errors,
        )


def _unit_tests_builtin(errors: list[str]) -> None:
    policy = builtin_policy()
    _assert(len(policy.rules) >= 4, f"builtin policy has too few rules: {len(policy.rules)}", errors)

    # PII residual is medium severity → outcome 'flag', NOT 'block'.
    text = "Reach me at alice@example.com or 13912345678."
    flags = policy.scan(text)
    kinds = sorted({f.category for f in flags})
    _assert("pii_residual" in kinds, f"expected pii_residual in {kinds}", errors)
    _assert(outcome_for(flags) == "flag", f"expected flag, got {outcome_for(flags)}", errors)

    # Self-harm intent is high severity → outcome 'block'.
    flags2 = policy.scan("I want to end my life today.")
    _assert(outcome_for(flags2) == "block", f"expected block, got {outcome_for(flags2)}", errors)

    # Plain prose: pass.
    flags3 = policy.scan("Today the weather is fine and I went for a walk.")
    _assert(outcome_for(flags3) == "pass", f"expected pass, got {outcome_for(flags3)}", errors)

    # Flags never echo the matched substring.
    for f in flags:
        d = f.to_dict()
        _assert(
            "alice@example.com" not in json.dumps(d) and "13912345678" not in json.dumps(d),
            "flag dict leaks the matched substring",
            errors,
        )


def _unit_tests_custom_policy(tmp_path: Path, errors: list[str]) -> None:
    custom = {
        "name": "test_custom",
        "version": "1.0",
        "rules": [
            {
                "name": "secret_word",
                "category": "leak",
                "severity": "high",
                "patterns": [r"\bbananafone\b"],
            }
        ],
    }
    custom_path = tmp_path / "custom.json"
    custom_path.write_text(json.dumps(custom), encoding="utf-8")

    loaded = load_policy_file(custom_path)
    _assert(len(loaded.rules) == 1, "custom policy should have 1 rule", errors)
    flags = loaded.scan("the bananafone is ringing")
    _assert(len(flags) == 1, f"custom rule should fire once, got {len(flags)}", errors)

    # Merging with built-in keeps both rule sets.
    combined = merge_policies(builtin_policy(), loaded)
    _assert(any(r.name == "secret_word" for r in combined.rules), "merge dropped custom rule", errors)
    _assert(any(r.name == "self_harm_intent_en" for r in combined.rules), "merge dropped builtin rule", errors)

    # select_policy(--no-builtin) without a custom file should hard-fail.
    crashed = False
    try:
        select_policy(use_builtin=False, custom_path=None)
    except SystemExit:
        crashed = True
    _assert(crashed, "select_policy(no_builtin, no_path) should exit", errors)


def _make_synthetic_record(root: Path) -> Path:
    record = root / "dlrs_test_mod_001"
    derived_text = record / "derived" / "text"
    derived_text.mkdir(parents=True, exist_ok=True)
    (derived_text / "voice_master.clean.txt").write_text(
        "Hello world.\n\nReach me at alice@example.com or 13912345678.\n",
        encoding="utf-8",
    )
    (record / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "dlrs-manifest/1.0",
                "record_id": "dlrs_test_mod_001",
                "created_at": "2026-04-26T09:00:00Z",
                "artifacts": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return record


def _e2e_test(errors: list[str]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.append("jsonschema not installed; install via tools/requirements.txt")
        return

    with tempfile.TemporaryDirectory() as tmp:
        record = _make_synthetic_record(Path(tmp))
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "moderation",
            "--record",
            str(record),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            errors.append(f"run_pipeline.py moderation exited {proc.returncode}: {proc.stderr.strip()}")
            return

        derived = record / "derived" / "moderation"
        mod_path = derived / "voice_master.moderation.json"
        desc_path = derived / "voice_master.moderation.descriptor.json"

        for p in (mod_path, desc_path):
            _assert(p.exists(), f"missing output {p}", errors)

        if mod_path.exists():
            payload = json.loads(mod_path.read_text(encoding="utf-8"))
            _assert(
                payload.get("outcome") == "flag",
                f"expected outcome=flag (from PII), got {payload.get('outcome')}",
                errors,
            )
            blob = mod_path.read_text(encoding="utf-8")
            _assert("alice@example.com" not in blob, "moderation.json leaked email", errors)
            _assert("13912345678" not in blob, "moderation.json leaked phone", errors)

        if desc_path.exists():
            d = json.loads(desc_path.read_text(encoding="utf-8"))
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            schema_errors = sorted(Draft202012Validator(schema).iter_errors(d), key=lambda e: e.path)
            for se in schema_errors:
                errors.append(
                    f"mod descriptor schema error at {'/'.join(map(str, se.path)) or '<root>'}: {se.message}"
                )
            _assert(d.get("pipeline") == "moderation", "descriptor.pipeline != moderation", errors)
            _assert(
                d.get("moderation_outcome") == "flag",
                f"descriptor.moderation_outcome should be 'flag', got {d.get('moderation_outcome')}",
                errors,
            )
            _assert(
                d.get("output", {}).get("path", "").startswith("derived/moderation/"),
                "descriptor.output.path doesn't start with derived/moderation/",
                errors,
            )


def main() -> int:
    errors: list[str] = []
    _unit_tests_outcome(errors)
    _unit_tests_builtin(errors)
    with tempfile.TemporaryDirectory() as tmp:
        _unit_tests_custom_policy(Path(tmp), errors)
    _e2e_test(errors)

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"test_moderation_pipeline: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("test_moderation_pipeline: rule engine + builtin + custom + end-to-end OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
