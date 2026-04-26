#!/usr/bin/env python3
"""Sanity tests for ``schemas/genesis.schema.json`` (.life Asset Genesis, v0.8).

Mirrors the structure of ``test_memory_atom_schema.py`` and
``test_life_package_schema.py``: build a known-good genesis document and
mutate it to provoke each schema-level rejection. The build/runtime
implementations (#101 + later) will validate every emitted genesis file
against the same schema, so these cases double as pre-flight checks
for those implementations.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "genesis.schema.json"


def _good_genesis() -> dict:
    return {
        "schema_version": "dlrs-life-genesis/0.1",
        "asset_id": "voice-master-v1",
        "asset_kind": "voice_clone",
        "method": {
            "name": "xtts-v2-finetune",
            "version": "1.2.3",
            "config_ref": "configs/voice-master-v1.yaml",
            "code_repo": "https://github.com/example/xtts-finetune",
            "code_commit": "108b50c1",
        },
        "source_inputs": [
            {
                "type": "recording",
                "ref": "raw/recording-2025-01-12.wav",
                "sha256": "0" * 64,
                "consent_ref": "consent/recording-2025-01-12.signed.pdf",
                "consent_scope": ["voice_clone", "interactive_chat"],
            },
            {
                "type": "base_model",
                "ref": "https://huggingface.co/coqui/XTTS-v2",
                "sha256": "1" * 64,
                "consent_ref": "not_applicable",
                "consent_scope": ["license_governed"],
                "license": "cc-by-nc-4.0",
                "source_url": "https://huggingface.co/coqui/XTTS-v2",
            },
        ],
        "compute": {
            "platform": "local-mac-m2",
            "operator": "alice@example.org",
            "started_at": "2026-04-01T08:00:00Z",
            "finished_at": "2026-04-01T09:30:00Z",
            "hosted_api_used": False,
            "data_left_local": True,
        },
        "consent_scope_checked": {
            "verified": True,
            "verifier": "tools/build_life_package.py",
            "verifier_version": "0.2.0",
            "verified_at": "2026-04-01T09:30:00Z",
            "scopes_used": ["voice_clone", "interactive_chat", "license_governed"],
        },
        "audit_event_ref": "audit/events.jsonl#L42",
        "audit_event_id": "01HW91QJTR4ETRBM3DNJK4Y9MA",
        "reproducibility_level": "param_identical",
        "consent_scope": ["voice_clone", "interactive_chat", "memorial_voice"],
        "base_model": {
            "name": "coqui/XTTS-v2",
            "license": "cc-by-nc-4.0",
            "sha256": "1" * 64,
            "source_url": "https://huggingface.co/coqui/XTTS-v2",
        },
    }


def _hosted_genesis() -> dict:
    """A hosted-API build, with hosted_api_providers populated."""
    g = _good_genesis()
    g["compute"]["hosted_api_used"] = True
    g["compute"]["data_left_local"] = False
    g["compute"]["hosted_api_providers"] = [
        {
            "name": "openai",
            "endpoint": "https://api.openai.com/v1/audio/speech",
            "purpose": "voice_synthesis_training",
            "data_retention_policy_ref": "https://openai.com/policies/api-data-usage-policies",
        }
    ]
    g["reproducibility_level"] = "not_reproducible"
    return g


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    cases: list[tuple[str, dict, bool]] = []

    cases.append(("good genesis (offline build, base model declared)", _good_genesis(), True))
    cases.append(("good genesis (hosted-API build with providers)", _hosted_genesis(), True))

    # Minimal valid: drop optional asset_kind, method.config_ref, base_model, notes.
    minimal = _good_genesis()
    minimal.pop("asset_kind")
    minimal["method"].pop("config_ref")
    minimal.pop("base_model")
    cases.append(("minimal valid (only required fields populated)", minimal, True))

    # 1. Missing schema_version -> reject.
    g = _good_genesis(); g.pop("schema_version")
    cases.append(("missing schema_version", g, False))

    # 2. Wrong schema_version constant -> reject.
    g = _good_genesis(); g["schema_version"] = "dlrs-life-genesis/0.2"
    cases.append(("wrong schema_version constant", g, False))

    # 3. asset_id pattern violation (uppercase) -> reject.
    g = _good_genesis(); g["asset_id"] = "Voice-Master-V1"
    cases.append(("asset_id starts uppercase", g, False))

    # 4. asset_id too short -> reject (pattern requires >=3 chars after first letter).
    g = _good_genesis(); g["asset_id"] = "ab"
    cases.append(("asset_id too short", g, False))

    # 5. method.name empty -> reject.
    g = _good_genesis(); g["method"]["name"] = ""
    cases.append(("method.name empty", g, False))

    # 6. method.code_commit not hex -> reject.
    g = _good_genesis(); g["method"]["code_commit"] = "not-a-hex-sha"
    cases.append(("method.code_commit not hex", g, False))

    # 7. source_inputs empty -> reject (D1=C requires at least the base model).
    g = _good_genesis(); g["source_inputs"] = []
    cases.append(("source_inputs empty", g, False))

    # 8. source_inputs[i].type outside enum -> reject.
    g = _good_genesis(); g["source_inputs"][0]["type"] = "voicemail"
    cases.append(("source_inputs[0].type unknown", g, False))

    # 9. source_inputs[i].sha256 wrong length -> reject.
    g = _good_genesis(); g["source_inputs"][0]["sha256"] = "0" * 32
    cases.append(("source_inputs[0].sha256 too short", g, False))

    # 10. source_inputs[i].consent_scope empty -> reject.
    g = _good_genesis(); g["source_inputs"][0]["consent_scope"] = []
    cases.append(("source_inputs[0].consent_scope empty", g, False))

    # 11. source_inputs[i].consent_scope value outside enum -> reject.
    g = _good_genesis(); g["source_inputs"][0]["consent_scope"] = ["voice_clone", "secret_use"]
    cases.append(("source_inputs[0].consent_scope value off-enum", g, False))

    # 12. source_inputs[i] additional unknown property -> reject.
    g = _good_genesis(); g["source_inputs"][0]["random_extra"] = 1
    cases.append(("source_inputs[0] unknown property", g, False))

    # 13. compute.hosted_api_used=true but no providers -> reject (allOf if/then).
    g = _good_genesis()
    g["compute"]["hosted_api_used"] = True
    g["compute"]["data_left_local"] = False
    cases.append(("hosted_api_used=true without providers", g, False))

    # 14. compute.hosted_api_used=true, providers empty array -> reject (minItems 1).
    g = _hosted_genesis(); g["compute"]["hosted_api_providers"] = []
    cases.append(("hosted_api_used=true, providers empty", g, False))

    # 15. compute.platform empty -> reject.
    g = _good_genesis(); g["compute"]["platform"] = ""
    cases.append(("compute.platform empty", g, False))

    # 16. compute.started_at wrong type -> reject (format date-time is informational
    # without FormatChecker, but the type=string constraint is structural).
    g = _good_genesis(); g["compute"]["started_at"] = 1735689600
    cases.append(("compute.started_at wrong type (number)", g, False))

    # 17. compute additional unknown property -> reject.
    g = _good_genesis(); g["compute"]["secret_field"] = "x"
    cases.append(("compute unknown property", g, False))

    # 18. consent_scope_checked.verified missing -> reject.
    g = _good_genesis(); g["consent_scope_checked"].pop("verified")
    cases.append(("consent_scope_checked.verified missing", g, False))

    # 19. consent_scope_checked.scopes_used empty -> reject.
    g = _good_genesis(); g["consent_scope_checked"]["scopes_used"] = []
    cases.append(("consent_scope_checked.scopes_used empty", g, False))

    # 20. consent_scope_checked.scopes_used off-enum -> reject.
    g = _good_genesis(); g["consent_scope_checked"]["scopes_used"] = ["mind_reading"]
    cases.append(("consent_scope_checked.scopes_used off-enum", g, False))

    # 21. audit_event_ref bad format (no #L) -> reject.
    g = _good_genesis(); g["audit_event_ref"] = "audit/events.jsonl:42"
    cases.append(("audit_event_ref wrong separator", g, False))

    # 22. audit_event_id empty -> reject.
    g = _good_genesis(); g["audit_event_id"] = ""
    cases.append(("audit_event_id empty", g, False))

    # 23. reproducibility_level off-enum -> reject (D3=C is graded but fixed).
    g = _good_genesis(); g["reproducibility_level"] = "best_effort"
    cases.append(("reproducibility_level off-enum", g, False))

    # 24. consent_scope empty -> reject.
    g = _good_genesis(); g["consent_scope"] = []
    cases.append(("consent_scope empty", g, False))

    # 25. consent_scope off-enum -> reject (D4=A is fixed).
    g = _good_genesis(); g["consent_scope"] = ["voice_clone", "live_chat"]
    cases.append(("consent_scope value off-enum", g, False))

    # 26. consent_scope duplicate values -> reject (uniqueItems).
    g = _good_genesis(); g["consent_scope"] = ["voice_clone", "voice_clone"]
    cases.append(("consent_scope duplicate values", g, False))

    # 27. base_model.sha256 wrong format -> reject.
    g = _good_genesis(); g["base_model"]["sha256"] = "abc123"
    cases.append(("base_model.sha256 wrong format", g, False))

    # 28. base_model.license empty -> reject.
    g = _good_genesis(); g["base_model"]["license"] = ""
    cases.append(("base_model.license empty", g, False))

    # 29. additionalProperties at top level -> reject.
    g = _good_genesis(); g["unknown_top_level"] = 1
    cases.append(("unknown top-level field", g, False))

    # 30. notes too long -> reject.
    g = _good_genesis(); g["notes"] = "x" * 5000
    cases.append(("notes > 4096 chars", g, False))

    failures = 0
    for name, doc, expect_valid in cases:
        errors = list(validator.iter_errors(doc))
        is_valid = not errors
        if is_valid != expect_valid:
            failures += 1
            print(f"FAIL  {name}: expected valid={expect_valid} got valid={is_valid}")
            for e in errors[:3]:
                print(f"        {e.message}")
        else:
            print(f"OK    {name}")

    print(f"\nrun: {len(cases)} cases, failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
