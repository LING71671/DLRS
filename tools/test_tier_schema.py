#!/usr/bin/env python3
"""Sanity tests for ``schemas/tier.schema.json`` (.life Tier Block, v0.8).

The tier schema exports two shapes via ``$defs``:

- ``tier_block`` — full tier object (score, level, name, glyph, dimensions,
  computed_at, computed_by) embedded in ``life-package.json`` post-integration.
- ``tier_dimensions`` — the six-dimension sub-object.

The top-level schema ``$ref``-s ``#/$defs/tier_block`` so a consumer that loads
the schema directly validates against the full block. This test suite uses the
top-level schema for ``tier_block`` cases and a sub-validator for the
``tier_dimensions``-only cases.

Pattern mirrors ``test_lifecycle_schema.py``: a known-good builder for each
shape, then negative mutations exercising every enum, every required field,
every score → level binding boundary, and the auto-computation guard on
``computed_by``.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "tier.schema.json"


def _top_validator(Draft202012Validator, schema: dict):
    return Draft202012Validator(schema)


def _dims_validator(Draft202012Validator, schema: dict):
    sub = {"$ref": "#/$defs/tier_dimensions", "$defs": schema["$defs"]}
    return Draft202012Validator(sub)


def _good_dimensions() -> dict:
    return {
        "identity_verification": "kyc_verified",
        "asset_completeness": "comprehensive",
        "consent_completeness": "notarized",
        "detail_level": "high_fidelity",
        "audit_chain_strength": "signed_chain",
        "jurisdiction_clarity": "declared",
    }


def _good_tier_block(score: int, level: str) -> dict:
    return {
        "score": score,
        "level": level,
        "name": "Main Sequence",
        "glyph": "★",
        "dimensions": _good_dimensions(),
        "computed_at": "2026-04-26T14:00:00Z",
        "computed_by": "tools/build_life_package.py@0.2.0",
    }


# Canonical (score, level) pairs from the Schema D appendix. One representative
# per tier, plus both boundaries of every range.
TIER_RANGES = [
    ("I", 0, 8),
    ("II", 9, 16),
    ("III", 17, 24),
    ("IV", 25, 32),
    ("V", 33, 40),
    ("VI", 41, 50),
    ("VII", 51, 60),
    ("VIII", 61, 68),
    ("IX", 69, 76),
    ("X", 77, 84),
    ("XI", 85, 92),
    ("XII", 93, 100),
]


def _validate(validator, instance: dict) -> list[str]:
    return [e.message for e in validator.iter_errors(instance)]


def _run() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    top = _top_validator(Draft202012Validator, schema)
    dims = _dims_validator(Draft202012Validator, schema)

    # cases is a list of (name, validator, instance, should_pass) tuples.
    cases: list[tuple[str, object, dict, bool]] = []

    # ----- tier_block: happy path for every tier -----
    for level, lo, hi in TIER_RANGES:
        cases.append((f"tier {level}: low boundary score={lo}", top, _good_tier_block(lo, level), True))
        cases.append((f"tier {level}: high boundary score={hi}", top, _good_tier_block(hi, level), True))

    # ----- tier_block negative: score → level mismatch at every boundary -----
    # For every adjacent pair of tiers, verify the boundary is not crossable.
    for (low_lvl, _lo, low_hi), (hi_lvl, hi_lo, _hi) in zip(TIER_RANGES, TIER_RANGES[1:]):
        # score belongs to low tier but level says high tier
        bad = _good_tier_block(low_hi, hi_lvl)
        cases.append((f"score {low_hi} declared {hi_lvl} (must be {low_lvl})", top, bad, False))
        # score belongs to high tier but level says low tier
        bad = _good_tier_block(hi_lo, low_lvl)
        cases.append((f"score {hi_lo} declared {low_lvl} (must be {hi_lvl})", top, bad, False))

    # ----- tier_block negative: missing fields -----
    for missing in ["score", "level", "name", "glyph", "dimensions", "computed_at", "computed_by"]:
        bad = _good_tier_block(55, "VII")
        bad.pop(missing)
        cases.append((f"tier_block missing {missing}", top, bad, False))

    # ----- tier_block negative: out-of-range score -----
    bad = _good_tier_block(55, "VII"); bad["score"] = -1
    cases.append(("tier_block score < 0 rejected", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["score"] = 101
    cases.append(("tier_block score > 100 rejected", top, bad, False))

    # ----- tier_block negative: wrong type for score -----
    bad = _good_tier_block(55, "VII"); bad["score"] = 55.5
    cases.append(("tier_block score must be integer (no float)", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["score"] = "55"
    cases.append(("tier_block score must be integer (no string)", top, bad, False))

    # ----- tier_block negative: level off-enum -----
    bad = _good_tier_block(55, "VII"); bad["level"] = "XIII"
    cases.append(("tier_block level XIII off-enum", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["level"] = "7"
    cases.append(("tier_block level Arabic numeral rejected", top, bad, False))

    # ----- tier_block negative: empty / overlong name and glyph -----
    bad = _good_tier_block(55, "VII"); bad["name"] = ""
    cases.append(("tier_block name empty", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["glyph"] = ""
    cases.append(("tier_block glyph empty", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["glyph"] = "G" * 17
    cases.append(("tier_block glyph too long", top, bad, False))

    # ----- tier_block negative: computed_by hand-rolled (no @ separator) -----
    bad = _good_tier_block(55, "VII"); bad["computed_by"] = "manual"
    cases.append(("tier_block computed_by missing @-separator", top, bad, False))
    bad = _good_tier_block(55, "VII"); bad["computed_by"] = "tools/build@"
    cases.append(("tier_block computed_by missing version", top, bad, False))

    # ----- tier_block negative: computed_at must be a string -----
    bad = _good_tier_block(55, "VII"); bad["computed_at"] = 1714137600
    cases.append(("tier_block computed_at must be a string (epoch rejected)", top, bad, False))

    # ----- tier_block negative: unknown top-level field -----
    bad = _good_tier_block(55, "VII"); bad["secret_grade"] = "AAA"
    cases.append(("tier_block additional property rejected", top, bad, False))

    # ----- tier_dimensions: happy path with each dimension at its lowest -----
    low = {
        "identity_verification": "unverified",
        "asset_completeness": "minimal",
        "consent_completeness": "none",
        "detail_level": "low_fidelity",
        "audit_chain_strength": "minimal",
        "jurisdiction_clarity": "unspecified",
    }
    cases.append(("tier_dimensions all-lowest valid", dims, low, True))

    # ----- tier_dimensions: happy path with each dimension at its highest -----
    high = {
        "identity_verification": "notarized",
        "asset_completeness": "archive_grade",
        "consent_completeness": "multi_party_attested",
        "detail_level": "cinematic",
        "audit_chain_strength": "notarized_chain",
        "jurisdiction_clarity": "court_recognized",
    }
    cases.append(("tier_dimensions all-highest valid", dims, high, True))

    # ----- tier_dimensions: missing each dimension -----
    for missing in [
        "identity_verification",
        "asset_completeness",
        "consent_completeness",
        "detail_level",
        "audit_chain_strength",
        "jurisdiction_clarity",
    ]:
        bad = _good_dimensions(); bad.pop(missing)
        cases.append((f"tier_dimensions missing {missing}", dims, bad, False))

    # ----- tier_dimensions: each enum off-value -----
    off_values = {
        "identity_verification": "passport_verified",
        "asset_completeness": "deluxe",
        "consent_completeness": "verbal",
        "detail_level": "ultra",
        "audit_chain_strength": "verified",
        "jurisdiction_clarity": "global",
    }
    for field, off in off_values.items():
        bad = _good_dimensions(); bad[field] = off
        cases.append((f"tier_dimensions {field}={off} off-enum", dims, bad, False))

    # ----- tier_dimensions: additional property rejected -----
    bad = _good_dimensions(); bad["future_dimension"] = "experimental"
    cases.append(("tier_dimensions additional property rejected", dims, bad, False))

    # ----- run all cases -----
    failures: list[str] = []
    for name, validator, instance, should_pass in cases:
        errors = _validate(validator, instance)
        passed = len(errors) == 0
        if passed != should_pass:
            failures.append(
                f"  - {name}: expected {'pass' if should_pass else 'fail'}, got "
                f"{'pass' if passed else 'fail'} ({errors!r})"
            )
    print(f"run: {len(cases)} cases, failures: {len(failures)}")
    for line in failures:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run())
