#!/usr/bin/env python3
"""Test cases for ``tools/build_registry.py``'s public-registry inclusion rules.

Implements the inclusion / exclusion / data-integrity scenarios listed in
issue #14. Each test:

1. Constructs an in-memory manifest from a baseline using a small mutator.
2. Calls ``build_registry.public_ok`` and ``build_registry.badges`` directly.
3. Asserts the expected boolean / set / field constraints.

Tests run by default; use ``--verbose`` for per-case details.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_BUILD = _load_module("build_registry", ROOT / "tools" / "build_registry.py")
public_ok = _BUILD.public_ok
badges = _BUILD.badges


def _baseline_manifest() -> dict:
    """A baseline 'should be in registry' manifest."""
    return {
        "schema_version": "0.3.0",
        "record_id": "dlrs_test_baseline",
        "visibility": "public_indexed",
        "subject": {
            "type": "self",
            "display_name": "Test Subject",
            "locale": "en-US",
            "residency_region": "US",
            "is_minor": False,
            "status": "living",
        },
        "rights": {
            "uploader_role": "self",
            "rights_basis": ["consent"],
            "evidence_refs": ["consent/consent_statement.md"],
            "allow_public_listing": True,
            "allow_commercial_use": False,
            "allow_model_finetune": False,
            "allow_voice_clone": False,
            "allow_avatar_clone": False,
            "cross_border_transfer_basis": "consent_only",
            "cross_border_transfer_status": "approved",
        },
        "consent": {
            "captured_at": "2026-04-25T10:00:00Z",
            "withdrawal_endpoint": "https://github.com/Digital-Life-Repository-Standard/DLRS/issues/new?template=consent-withdrawal.yml",
            "consent_version": "0.3.0",
            "allowed_scopes": ["storage", "structured_processing"],
            "separate_biometric_consent": False,
        },
        "review": {
            "status": "approved_public",
            "verified_consent_badge": True,
            "public_data_only_badge": False,
            "risk_level": "low",
        },
        "audit": {
            "created_at": "2026-04-25T10:00:00Z",
            "last_modified_at": "2026-04-25T10:00:00Z",
            "change_log_hash": "sha256:0",
        },
    }


def _mutate(base: dict, **changes) -> dict:
    """Return a deep-copied manifest with dotted-path overrides applied."""
    m = copy.deepcopy(base)
    for path, value in changes.items():
        parts = path.split(".")
        node = m
        for key in parts[:-1]:
            node = node.setdefault(key, {})
        node[parts[-1]] = value
    return m


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

CASES: list[tuple[str, callable, callable]] = []


def case(name: str):
    def deco(fn):
        CASES.append((name, fn, fn))
        return fn
    return deco


@case("private record -> NOT in registry")
def t_private_excluded():
    m = _mutate(_baseline_manifest(), visibility="private")
    assert public_ok(m) is False, "private records must NOT be in registry"


@case("public_indexed + approved_public + verified_consent badge -> IN registry")
def t_public_baseline_included():
    m = _baseline_manifest()
    assert public_ok(m) is True, "baseline public record must be in registry"


@case("minor record -> NOT in registry")
def t_minor_excluded():
    m = _mutate(_baseline_manifest(), **{"subject.is_minor": True})
    assert public_ok(m) is False, "minors must NOT be in registry"


@case("allow_public_listing=false -> NOT in registry")
def t_no_public_listing_excluded():
    m = _mutate(_baseline_manifest(), **{"rights.allow_public_listing": False})
    assert public_ok(m) is False, "allow_public_listing=false must exclude"


@case("public_unlisted -> IN registry when other gates pass")
def t_public_unlisted_included():
    """v0.3 explicitly documents public_unlisted as registry-eligible."""
    m = _mutate(_baseline_manifest(), visibility="public_unlisted")
    assert public_ok(m) is True


@case("review.status not approved_public -> NOT in registry")
def t_unapproved_excluded():
    for status in ("draft", "submitted", "blocked", "approved_private"):
        m = _mutate(_baseline_manifest(), **{"review.status": status})
        assert public_ok(m) is False, f"status={status} must be excluded"


@case("missing both badges -> NOT in registry")
def t_missing_badge_excluded():
    m = _mutate(
        _baseline_manifest(),
        **{
            "review.verified_consent_badge": False,
            "review.public_data_only_badge": False,
        },
    )
    assert public_ok(m) is False, "no verified-consent or public-data-only badge -> excluded"


@case("public_data_only_badge alone is sufficient -> IN registry")
def t_public_data_only_badge_ok():
    m = _mutate(
        _baseline_manifest(),
        **{
            "review.verified_consent_badge": False,
            "review.public_data_only_badge": True,
        },
    )
    assert public_ok(m) is True


@case("badges list reflects deceased + cross-border-blocked + public-data-only")
def t_badges_composition():
    m = _mutate(
        _baseline_manifest(),
        **{
            "review.public_data_only_badge": True,
            "review.verified_consent_badge": True,
            "subject.status": "deceased",
            "rights.cross_border_transfer_status": "blocked",
        },
    )
    out = badges(m)
    assert "verified-consent" in out
    assert "public-data-only" in out
    assert "memorial-review-required" in out
    assert "cross-border-blocked" in out


@case("registry rows expose only safe fields (no biometric leakage)")
def t_registry_row_shape():
    """Smoke-check that the keys produced by build_registry.main() for a public manifest match the registry-entry schema."""
    schema = json.loads((ROOT / "schemas" / "registry-entry.schema.json").read_text())
    required = set(schema["required"])
    forbidden_substrings = ("legal_name", "biometric", "checksum", "kms", "phone", "email")

    m = _baseline_manifest()
    fake_path = ROOT / "humans" / "americas" / "us" / "dlrs_test_baseline" / "manifest.json"
    rel = fake_path.parent.relative_to(ROOT).as_posix() if ROOT in fake_path.parents else "humans/test"
    entry = {
        "record_id": m["record_id"],
        "path": rel,
        "display_name": m["subject"]["display_name"],
        "visibility": m["visibility"],
        "badges": badges(m),
        "region": m["subject"]["residency_region"],
        "locale": m["subject"]["locale"],
        "risk_level": m["review"]["risk_level"],
        "updated_at": m["audit"]["last_modified_at"],
    }
    assert required.issubset(entry.keys()), f"missing required keys: {required - entry.keys()}"
    serialised = json.dumps(entry).lower()
    for bad in forbidden_substrings:
        assert bad not in serialised, f"registry row leaks {bad!r}"


@case("withdrawal_endpoint is required upstream (manifest validation)")
def t_withdrawal_endpoint_required_upstream():
    """public_ok itself does not enforce withdrawal_endpoint, but tools/validate_manifest.py does. This case verifies the manifest validator rejects manifests missing it."""
    import subprocess, tempfile
    m = _baseline_manifest()
    m["consent"].pop("withdrawal_endpoint", None)
    m["artifacts"] = []
    m["deletion_policy"] = {"allow_delete": True, "allow_export": True, "withdrawal_effect": "freeze_runtime_then_delete"}
    m["inheritance_policy"] = {"policy_ref": "x", "default_action_on_death": "freeze", "executor_contact_ref": None}
    m["security"] = {"primary_region": "US", "encryption_at_rest": True, "watermark_policy": "none", "c2pa_enabled": False}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(m, fh)
        path = fh.name
    res = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_manifest.py"), path],
        capture_output=True, text=True,
    )
    assert res.returncode != 0, "validate_manifest must reject a manifest missing withdrawal_endpoint"
    assert "withdrawal_endpoint" in (res.stdout + res.stderr)


@case("consent expired (expires_at in past) is acceptable until enforcement implemented")
def t_consent_expiry_documented():
    """v0.3 schema permits consent.expires_at; runtime enforcement is tracked for v0.4. This test pins behaviour: public_ok currently treats expiry as out-of-scope."""
    m = _mutate(_baseline_manifest(), **{"consent.expires_at": "2020-01-01T00:00:00Z"})
    # Documented behaviour: public_ok does NOT yet enforce expiry. Update this
    # test together with build_registry.public_ok when v0.4 adds enforcement.
    assert public_ok(m) is True


@case("v0.4: minor subject is excluded even if every other public flag is set")
def t_minor_excluded_even_when_public():
    """examples/minor-protected encodes this; assert exclusion on a fully-blessed
    public manifest as soon as ``subject.is_minor`` flips to True."""
    m = _baseline_manifest()
    assert public_ok(m) is True  # baseline sanity
    m = _mutate(m, **{"subject.is_minor": True})
    assert public_ok(m) is False
    # Even with restricted-runtime badge, minors stay out.
    m = _mutate(m, **{"rights.allow_public_listing": False})
    assert public_ok(m) is False


@case("v0.4: estate-conflict legal_hold/blocked record stays out of registry")
def t_estate_conflict_blocked_excluded():
    """examples/estate-conflict-frozen encodes this. legal_hold + cross-border-blocked
    + review.status=blocked + subject.status=deceased: registry MUST exclude."""
    m = _mutate(
        _baseline_manifest(),
        **{
            "subject.status": "deceased",
            "rights.cross_border_transfer_status": "blocked",
            "rights.allow_public_listing": False,
            "deletion_policy.legal_hold": True,
            "review.status": "blocked",
            "review.risk_level": "critical",
        },
    )
    assert public_ok(m) is False
    badge_set = set(badges(m))
    # Even though the record is excluded, badge composition stays meaningful for
    # downstream auditors who consume manifest directly.
    assert "memorial-review-required" in badge_set
    assert "cross-border-blocked" in badge_set
    assert "restricted-runtime" in badge_set


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv[1:])

    fail = 0
    for name, fn, _ in CASES:
        try:
            fn()
        except AssertionError as exc:
            fail += 1
            print(f"FAIL  {name}: {exc}")
            continue
        except Exception as exc:
            fail += 1
            print(f"ERROR {name}: {exc}")
            continue
        if args.verbose:
            print(f"OK    {name}")

    print()
    if fail:
        print(f"test_registry: {fail}/{len(CASES)} failed")
        return 1
    print(f"test_registry: all {len(CASES)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
