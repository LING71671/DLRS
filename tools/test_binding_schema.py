#!/usr/bin/env python3
"""Sanity tests for ``schemas/binding.schema.json`` (v0.8 sub-issue #103).

Exercises the v0.8 `dlrs-life-binding/0.1` shape:

* every required top-level field
* hybrid capability-name vocabulary (core enum + ``x-`` extensions)
* engine_compatibility ``strict`` self-decision (decision D2=C)
* hard_constraints fail-close on unknown non-``x-`` keys (decision D4=C)
* surface three-field shape (decision Topic 4 D4=C)
* hosted_api_preference structure (decision D5=A AND-gate, issuer half)
* ``additionalProperties: false`` at every closed level

Each case is a tuple ``(name, doc, expect_valid)``. The driver counts
mismatches and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "binding.schema.json"


def _good_capability() -> dict:
    return {
        "asset_id": "voice-master-v1",
        "engine_compatibility": [
            {"name": "xtts-v2", "version_range": "^2.0.0", "strict": True, "engine_kind": "user_installed"}
        ],
        "params": {"temperature": 0.7},
    }


def _good_binding() -> dict:
    return {
        "schema_version": "dlrs-life-binding/0.1",
        "binding_version": "0.1.0",
        "minimum_runtime_version": "0.1",
        "capabilities": {
            "voice_synthesis": _good_capability(),
            "memory_recall": {
                "asset_id": "memory-atoms-v1",
                "engine_compatibility": [
                    {"name": "qdrant-local", "version_range": ">=1.5 <2"}
                ],
            },
            "x-custom_persona": {
                "asset_id": "persona-v1",
                "engine_compatibility": [
                    {"name": "ollama", "version_range": "^0.5"}
                ],
            },
        },
        "orchestration": {
            "default_llm": {"name": "llama3", "version_range": "^3.0"},
            "minimum_llm_capabilities": ["chat", "function_calling"],
            "context_strategy": "rolling_window",
            "max_context_tokens": 8000,
        },
        "hard_constraints": {
            "no_image_generation": True,
            "no_voice_clone_for_third_party": True,
            "max_memory_horizon_days": 365,
            "geo_restrictions": ["CN", "EU"],
            "x-tenant_only": True,
        },
        "surface": {
            "supported": ["chat", "voice_chat", "avatar_2d"],
            "preferred": "voice_chat",
            "minimum_required": "chat",
            "ui_hints": {
                "disclosure_label": "I am an AI digital life of Alice.",
                "color_scheme": "auto",
            },
        },
        "hosted_api_preference": {
            "allowed": True,
            "preferred_for": ["voice_synthesis"],
            "must_be_local_for": ["memory_recall"],
            "providers_whitelist_ref": "policy/hosted_api.json",
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

    cases: list[tuple[str, dict, bool]] = []

    # ----- happy paths -----
    cases.append(("good binding (full)", _good_binding(), True))

    # minimal binding: only required fields
    minimal = {
        "schema_version": "dlrs-life-binding/0.1",
        "binding_version": "0.1.0",
        "minimum_runtime_version": "0.1",
        "capabilities": {"chat": _good_capability()},
        "hard_constraints": {},
        "surface": {"supported": ["chat"], "preferred": "chat", "minimum_required": "chat"},
    }
    cases.append(("minimal binding", minimal, True))

    # x- capability only (legal extension namespace)
    g = _good_binding(); g["capabilities"] = {"x-custom_only": _good_capability()}
    cases.append(("x-only capability set", g, True))

    # engine entry without strict (default true) is fine
    g = _good_binding()
    g["capabilities"]["voice_synthesis"]["engine_compatibility"][0].pop("strict")
    cases.append(("engine without explicit strict (default true)", g, True))

    # ----- top-level required missing -----
    for missing in ("schema_version", "binding_version", "minimum_runtime_version", "capabilities", "hard_constraints", "surface"):
        g = _good_binding(); g.pop(missing)
        cases.append((f"missing top-level {missing}", g, False))

    # wrong schema_version
    g = _good_binding(); g["schema_version"] = "dlrs-life-binding/0.2"
    cases.append(("schema_version wrong", g, False))

    # binding_version not semver
    g = _good_binding(); g["binding_version"] = "v1"
    cases.append(("binding_version not semver", g, False))

    # minimum_runtime_version bad shape
    g = _good_binding(); g["minimum_runtime_version"] = "latest"
    cases.append(("minimum_runtime_version not semver", g, False))

    # ----- capabilities -----
    g = _good_binding(); g["capabilities"] = {}
    cases.append(("capabilities empty", g, False))

    # unknown core capability without x- prefix -> reject (D1=C hybrid)
    g = _good_binding(); g["capabilities"]["mind_reading"] = _good_capability()
    cases.append(("unknown non-x capability rejected", g, False))

    # x- prefix with disallowed chars
    g = _good_binding(); g["capabilities"]["x-Bad_Name"] = _good_capability()
    cases.append(("x- capability uppercase rejected", g, False))

    # capability missing asset_id
    g = _good_binding(); g["capabilities"]["voice_synthesis"].pop("asset_id")
    cases.append(("capability missing asset_id", g, False))

    # asset_id pattern violation
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["asset_id"] = "Voice"
    cases.append(("asset_id uppercase rejected", g, False))

    # capability missing engine_compatibility
    g = _good_binding(); g["capabilities"]["voice_synthesis"].pop("engine_compatibility")
    cases.append(("capability missing engine_compatibility", g, False))

    # engine_compatibility empty -> reject
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["engine_compatibility"] = []
    cases.append(("engine_compatibility empty", g, False))

    # engine entry missing required
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["engine_compatibility"][0].pop("name")
    cases.append(("engine entry missing name", g, False))
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["engine_compatibility"][0].pop("version_range")
    cases.append(("engine entry missing version_range", g, False))

    # engine_kind off-enum
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["engine_compatibility"][0]["engine_kind"] = "magic"
    cases.append(("engine_kind off-enum", g, False))

    # capability additionalProperties=false
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["random"] = 1
    cases.append(("capability unknown field", g, False))

    # tier_floor pattern
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["tier_floor"] = "VII"
    cases.append(("tier_floor VII (valid roman)", g, True))
    g = _good_binding(); g["capabilities"]["voice_synthesis"]["tier_floor"] = "13"
    cases.append(("tier_floor not roman", g, False))

    # ----- orchestration -----
    g = _good_binding(); g["orchestration"]["context_strategy"] = "magic"
    cases.append(("orchestration.context_strategy off-enum", g, False))

    g = _good_binding(); g["orchestration"]["minimum_llm_capabilities"] = []
    cases.append(("orchestration.minimum_llm_capabilities empty", g, False))

    g = _good_binding(); g["orchestration"]["minimum_llm_capabilities"] = ["chat", "chat"]
    cases.append(("orchestration.minimum_llm_capabilities duplicates", g, False))

    g = _good_binding(); g["orchestration"]["max_context_tokens"] = 100
    cases.append(("orchestration.max_context_tokens below floor", g, False))

    g = _good_binding(); g["orchestration"]["unknown"] = 1
    cases.append(("orchestration unknown field", g, False))

    # ----- hard_constraints (decision D4=C fail-close) -----
    g = _good_binding(); g["hard_constraints"]["no_image_generation"] = False
    cases.append(("hard_constraints known key with explicit false (allowed)", g, True))

    g = _good_binding(); g["hard_constraints"]["totally_unknown_key"] = True
    cases.append(("hard_constraints unknown non-x key REJECTED (fail-close)", g, False))

    g = _good_binding(); g["hard_constraints"]["x-anything"] = "any value"
    cases.append(("hard_constraints x-prefixed unknown key allowed", g, True))

    g = _good_binding(); g["hard_constraints"]["x-Bad"] = True
    cases.append(("hard_constraints x- with uppercase rejected", g, False))

    # ----- surface (Topic 4 D4=C three fields) -----
    for field in ("supported", "preferred", "minimum_required"):
        g = _good_binding(); g["surface"].pop(field)
        cases.append((f"surface missing {field}", g, False))

    g = _good_binding(); g["surface"]["supported"] = []
    cases.append(("surface.supported empty", g, False))

    g = _good_binding(); g["surface"]["supported"] = ["chat", "chat"]
    cases.append(("surface.supported duplicates", g, False))

    g = _good_binding(); g["surface"]["preferred"] = "telepathy"
    cases.append(("surface.preferred off-enum", g, False))

    g = _good_binding(); g["surface"]["minimum_required"] = "telepathy"
    cases.append(("surface.minimum_required off-enum", g, False))

    g = _good_binding(); g["surface"]["ui_hints"]["color_scheme"] = "rainbow"
    cases.append(("surface.ui_hints.color_scheme off-enum", g, False))

    g = _good_binding(); g["surface"]["ui_hints"]["unknown"] = 1
    cases.append(("surface.ui_hints unknown field", g, False))

    g = _good_binding(); g["surface"]["unknown"] = 1
    cases.append(("surface unknown field", g, False))

    # ----- hosted_api_preference (decision D5=A) -----
    g = _good_binding(); g["hosted_api_preference"].pop("allowed")
    cases.append(("hosted_api_preference missing allowed", g, False))

    g = _good_binding(); g["hosted_api_preference"]["preferred_for"] = ["a", "a"]
    cases.append(("hosted_api_preference.preferred_for duplicates", g, False))

    g = _good_binding(); g["hosted_api_preference"]["must_be_local_for"] = []
    cases.append(("hosted_api_preference.must_be_local_for empty array (uniqueItems-only constraint)", g, True))

    g = _good_binding(); g["hosted_api_preference"]["providers_whitelist_ref"] = ""
    cases.append(("hosted_api_preference.providers_whitelist_ref empty", g, False))

    # Cross-schema convention: path-inside-.life fields reject absolute paths
    # and `..` segments at the schema layer (matches life-package.schema.json
    # contents[].path and lifecycle.schema.json mutation_log_ref).
    g = _good_binding(); g["hosted_api_preference"]["providers_whitelist_ref"] = "/etc/passwd"
    cases.append(("hosted_api_preference.providers_whitelist_ref absolute path", g, False))

    g = _good_binding(); g["hosted_api_preference"]["providers_whitelist_ref"] = "../etc/passwd"
    cases.append(("hosted_api_preference.providers_whitelist_ref parent-dir traversal", g, False))

    g = _good_binding(); g["hosted_api_preference"]["providers_whitelist_ref"] = "policy/../etc/passwd"
    cases.append(("hosted_api_preference.providers_whitelist_ref embedded `..` segment", g, False))

    g = _good_binding(); g["hosted_api_preference"]["unknown"] = 1
    cases.append(("hosted_api_preference unknown field", g, False))

    # allowed:false binding (no preferred_for is fine without it)
    g = _good_binding()
    g["hosted_api_preference"] = {"allowed": False, "must_be_local_for": ["voice_synthesis"]}
    cases.append(("hosted_api_preference allowed=false (issuer-side ban)", g, True))

    # ----- top-level additionalProperties -----
    g = _good_binding(); g["unknown_top_level"] = 1
    cases.append(("unknown top-level field", g, False))

    failures = 0
    for name, doc, expect_valid in cases:
        errors = list(validator.iter_errors(doc))
        ok = len(errors) == 0
        if ok != expect_valid:
            failures += 1
            print(f"FAIL  {name}  (got valid={ok}, expected valid={expect_valid})")
            for err in errors[:3]:
                print(f"      - {err.message}  at {list(err.path)}")
        else:
            print(f"OK    {name}")
    print(f"\nrun: {len(cases)} cases, failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
