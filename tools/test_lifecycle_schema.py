#!/usr/bin/env python3
"""Sanity tests for ``schemas/lifecycle.schema.json`` (.life Asset Lifecycle, v0.8).

The lifecycle schema is a definitions library — its top-level shape is an
empty object, and all real validation happens via the four `$defs` shapes
exported under ``#/$defs/{package_lifecycle, asset_lifecycle, mutation_event,
cascade_index}``. This test suite builds a known-good example for each shape,
mutates it, and confirms the validator accepts/rejects as expected.

Pattern mirrors test_genesis_schema.py: 3-4 happy-path cases per shape, plus
~6 negative cases per shape exercising the conditional rules and enums.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "lifecycle.schema.json"


def _validator_for(defs_name: str, schema: dict):
    from jsonschema import Draft202012Validator
    sub = {"$ref": f"#/$defs/{defs_name}", "$defs": schema["$defs"]}
    return Draft202012Validator(sub)


def _good_package_lifecycle() -> dict:
    return {
        "version": "2.3.0",
        "supersedes": [
            {
                "package_id": "dlrs_alice_main",
                "version": "2.2.1",
                "sha256": "0" * 64,
            }
        ],
        "lifecycle_state": "active",
        "frozen": False,
        "memorial_metadata": None,
        "recommended_re_consent_after": "2027-04-01T00:00:00Z",
    }


def _good_memorial_package_lifecycle() -> dict:
    return {
        "version": "3.0.0",
        "supersedes": [],
        "lifecycle_state": "memorial",
        "frozen": True,
        "memorial_metadata": {
            "triggered_at": "2026-04-26T14:00:00Z",
            "trigger_kind": "executor",
            "trigger_actor": "executor@example.org",
            "evidence_ref": "consent/death-certificate-alice.signed.pdf",
            "dispute_window_ends_at": "2026-05-03T14:00:00Z",
            "dispute_window_status": "open",
            "executor_can_extend": True,
        },
    }


def _good_asset_lifecycle() -> dict:
    return {
        "version": "1.3.0",
        "supersedes": ["voice-master-v0"],
        "created_at": "2025-02-03T16:00:00Z",
        "last_mutation_at": "2026-04-20T00:00:00Z",
        "mutation_log_ref": "lifecycle/voice-master-v1.mutations.jsonl",
        "expires_at": "2027-02-03T00:00:00Z",
        "state": "active",
    }


def _good_tainted_asset_lifecycle() -> dict:
    return {
        "version": "1.3.0",
        "created_at": "2025-02-03T16:00:00Z",
        "state": "tainted",
        "tainted_reason": "source_input recording-2025-01-12.wav was withdrawn at 2026-04-01T08:00:00Z",
    }


def _good_mutation_event(action: str = "asset_created") -> dict:
    base = {
        "schema_version": "dlrs-life-mutation/0.1",
        "ts": "2026-04-26T14:30:00Z",
        "asset_id": "voice-master-v1",
        "action": action,
        "actor": "alice@example.org",
        "audit_event_ref": "audit/events.jsonl#L57",
        "audit_event_id": "01HW91W5GV5Q8E8H0G11M3D9YZ",
    }
    if action == "state_changed":
        base["from_state"] = "active"
        base["to_state"] = "tainted"
        base["reason"] = "source input withdrawn"
    elif action in ("input_added", "input_withdrawn"):
        base["input_ref"] = "raw/recording-2025-01-12.wav"
    elif action == "superseded_by":
        base["successor_asset_id"] = "voice-master-v2"
    return base


def _good_cascade_index() -> dict:
    return {
        "schema_version": "dlrs-life-cascade-index/0.1",
        "generated_at": "2026-04-26T14:30:00Z",
        "entries": [
            {
                "source_input_ref": "raw/recording-2025-01-12.wav",
                "source_input_sha256": "0" * 64,
                "derived_assets": ["voice-master-v1", "voice-memorial-v1"],
            }
        ],
    }


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    pkg_v = _validator_for("package_lifecycle", schema)
    asset_v = _validator_for("asset_lifecycle", schema)
    mut_v = _validator_for("mutation_event", schema)
    cas_v = _validator_for("cascade_index", schema)

    cases: list[tuple[str, "Draft202012Validator", dict, bool]] = []

    # ----- package_lifecycle -----
    cases.append(("pkg: good active", pkg_v, _good_package_lifecycle(), True))
    cases.append(("pkg: good memorial with metadata", pkg_v, _good_memorial_package_lifecycle(), True))

    # state=memorial requires memorial_metadata + frozen=true
    bad = _good_memorial_package_lifecycle(); bad["memorial_metadata"] = None
    cases.append(("pkg: memorial without metadata", pkg_v, bad, False))
    bad = _good_memorial_package_lifecycle(); bad["frozen"] = False
    cases.append(("pkg: memorial without frozen=true", pkg_v, bad, False))

    # state=frozen requires frozen=true
    bad = _good_package_lifecycle(); bad["lifecycle_state"] = "frozen"; bad["frozen"] = False
    cases.append(("pkg: state=frozen but frozen=false", pkg_v, bad, False))

    # supersedes max 1 (D2=C: merge forbidden)
    bad = _good_package_lifecycle()
    bad["supersedes"] = [
        {"package_id": "p1", "version": "1.0.0", "sha256": "0" * 64},
        {"package_id": "p2", "version": "1.0.0", "sha256": "1" * 64},
    ]
    cases.append(("pkg: supersedes has 2 entries (merge forbidden)", pkg_v, bad, False))

    # version not semver
    bad = _good_package_lifecycle(); bad["version"] = "v2-prerelease"
    cases.append(("pkg: version not semver", pkg_v, bad, False))

    # lifecycle_state off-enum
    bad = _good_package_lifecycle(); bad["lifecycle_state"] = "buried"
    cases.append(("pkg: lifecycle_state off-enum", pkg_v, bad, False))

    # supersedes_entry sha256 wrong format
    bad = _good_package_lifecycle(); bad["supersedes"][0]["sha256"] = "abc"
    cases.append(("pkg: supersedes[0].sha256 too short", pkg_v, bad, False))

    # additionalProperties=false at top level
    bad = _good_package_lifecycle(); bad["secret_field"] = 1
    cases.append(("pkg: unknown field rejected", pkg_v, bad, False))

    # memorial_metadata trigger_kind off-enum
    bad = _good_memorial_package_lifecycle(); bad["memorial_metadata"]["trigger_kind"] = "neighbor"
    cases.append(("pkg: memorial trigger_kind off-enum", pkg_v, bad, False))

    # memorial_metadata dispute_window_status off-enum
    bad = _good_memorial_package_lifecycle(); bad["memorial_metadata"]["dispute_window_status"] = "frozen"
    cases.append(("pkg: dispute_window_status off-enum", pkg_v, bad, False))

    # active state with non-null memorial_metadata MUST be rejected (spec §4.3
    # says "MUST be null otherwise"). The schema enforces this via an `else`
    # clause on the memorial allOf.
    bad = _good_package_lifecycle()
    bad["memorial_metadata"] = {
        "triggered_at": "2026-04-26T14:00:00Z",
        "trigger_kind": "executor",
    }
    cases.append(("pkg: active state with non-null memorial_metadata", pkg_v, bad, False))

    # ----- asset_lifecycle -----
    cases.append(("asset: good active", asset_v, _good_asset_lifecycle(), True))
    cases.append(("asset: good tainted with reason", asset_v, _good_tainted_asset_lifecycle(), True))

    # state=tainted requires tainted_reason
    bad = _good_tainted_asset_lifecycle(); bad.pop("tainted_reason")
    cases.append(("asset: tainted without reason", asset_v, bad, False))

    # state off-enum (asset-level enum excludes 'expired'/'memorial')
    bad = _good_asset_lifecycle(); bad["state"] = "expired"
    cases.append(("asset: state=expired (package-only) rejected at asset level", asset_v, bad, False))

    # supersedes max 1 (use valid asset_ids so we test maxItems specifically)
    bad = _good_asset_lifecycle(); bad["supersedes"] = ["voice-master-v0", "voice-master-v1"]
    cases.append(("asset: supersedes has 2 entries", asset_v, bad, False))

    # supersedes items MUST match asset_id pattern (cross-schema consistency
    # with mutation_event.asset_id, cascade_index.derived_assets, genesis.asset_id).
    bad = _good_asset_lifecycle(); bad["supersedes"] = ["X"]
    cases.append(("asset: supersedes item violates asset_id pattern", asset_v, bad, False))

    # mutation_log_ref pattern violation
    bad = _good_asset_lifecycle(); bad["mutation_log_ref"] = "audit/voice.jsonl"
    cases.append(("asset: mutation_log_ref wrong path", asset_v, bad, False))

    # mutation_log_ref MUST reject `..` path-traversal (defense in depth,
    # matches the convention used by life-package.schema.json contents[].path).
    bad = _good_asset_lifecycle(); bad["mutation_log_ref"] = "lifecycle/../etc/passwd.mutations.jsonl"
    cases.append(("asset: mutation_log_ref with .. traversal rejected", asset_v, bad, False))

    # version not semver
    bad = _good_asset_lifecycle(); bad["version"] = "1.3"
    cases.append(("asset: version not semver", asset_v, bad, False))

    # additionalProperties=false
    bad = _good_asset_lifecycle(); bad["secret_field"] = 1
    cases.append(("asset: unknown field rejected", asset_v, bad, False))

    # ----- mutation_event -----
    cases.append(("mut: good asset_created", mut_v, _good_mutation_event("asset_created"), True))
    cases.append(("mut: good state_changed", mut_v, _good_mutation_event("state_changed"), True))
    cases.append(("mut: good input_withdrawn", mut_v, _good_mutation_event("input_withdrawn"), True))
    cases.append(("mut: good superseded_by", mut_v, _good_mutation_event("superseded_by"), True))

    # state_changed requires from_state + to_state
    bad = _good_mutation_event("state_changed"); bad.pop("from_state")
    cases.append(("mut: state_changed without from_state", mut_v, bad, False))

    # input_added requires input_ref
    bad = _good_mutation_event("input_added"); bad.pop("input_ref")
    cases.append(("mut: input_added without input_ref", mut_v, bad, False))

    # superseded_by requires successor_asset_id
    bad = _good_mutation_event("superseded_by"); bad.pop("successor_asset_id")
    cases.append(("mut: superseded_by without successor_asset_id", mut_v, bad, False))

    # action off-enum
    bad = _good_mutation_event("asset_created"); bad["action"] = "asset_deleted"
    cases.append(("mut: action off-enum", mut_v, bad, False))

    # schema_version wrong
    bad = _good_mutation_event("asset_created"); bad["schema_version"] = "dlrs-life-mutation/0.2"
    cases.append(("mut: wrong schema_version", mut_v, bad, False))

    # asset_id pattern violation
    bad = _good_mutation_event("asset_created"); bad["asset_id"] = "Voice-Master"
    cases.append(("mut: asset_id uppercase", mut_v, bad, False))

    # additionalProperties=false
    bad = _good_mutation_event("asset_created"); bad["random"] = 1
    cases.append(("mut: unknown field rejected", mut_v, bad, False))

    # audit_event_ref must be 1-based (matches the repo-wide convention used by
    # life-package, memory-atom, entity-graph-* schemas; #L0 is rejected).
    bad = _good_mutation_event("asset_created"); bad["audit_event_ref"] = "audit/events.jsonl#L0"
    cases.append(("mut: audit_event_ref points at #L0 (must be 1-based)", mut_v, bad, False))

    # ----- cascade_index -----
    cases.append(("cas: good", cas_v, _good_cascade_index(), True))

    # schema_version wrong
    bad = _good_cascade_index(); bad["schema_version"] = "dlrs-life-cascade-index/0.2"
    cases.append(("cas: wrong schema_version", cas_v, bad, False))

    # entries empty list of derived_assets
    bad = _good_cascade_index(); bad["entries"][0]["derived_assets"] = []
    cases.append(("cas: derived_assets empty", cas_v, bad, False))

    # entries duplicate derived_assets
    bad = _good_cascade_index(); bad["entries"][0]["derived_assets"] = ["voice-master-v1", "voice-master-v1"]
    cases.append(("cas: derived_assets has duplicate", cas_v, bad, False))

    # source_input_sha256 wrong format
    bad = _good_cascade_index(); bad["entries"][0]["source_input_sha256"] = "xyz"
    cases.append(("cas: source_input_sha256 too short", cas_v, bad, False))

    # entries[i] additionalProperties=false
    bad = _good_cascade_index(); bad["entries"][0]["secret"] = 1
    cases.append(("cas: entry unknown field rejected", cas_v, bad, False))

    # asset id pattern violation in derived_assets
    bad = _good_cascade_index(); bad["entries"][0]["derived_assets"] = ["Voice-Master-V1"]
    cases.append(("cas: derived asset id uppercase", cas_v, bad, False))

    failures = 0
    for name, validator, doc, expect_valid in cases:
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
