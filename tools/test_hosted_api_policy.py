#!/usr/bin/env python3
"""Tests for the hosted-API opt-in policy gate (issue #59).

Layers:

1. **Schema/golden** — a representative valid policy passes JSON-Schema
   validation; missing required fields, unknown providers, and bad
   pipeline names fail.
2. **Default-deny** — when no ``policy/hosted_api.json`` exists,
   :func:`assert_allowed` raises :class:`HostedApiNotAllowed`.
3. **opt_in=false short-circuits** every other field.
4. **Provider whitelist** — provider not in ``allowed_providers`` is
   denied even when ``opt_in=true``.
5. **Pipeline whitelist** — pipeline not in ``allowed_pipelines`` is
   denied even when provider matches.
6. **Time bounds** — ``now < issued_at`` or ``now >= expires_at`` deny;
   correct interval permits.
7. **Successful gate** — when everything matches, returns the parsed
   :class:`HostedApiPolicy` instance; ``list_allowed_providers`` mirrors
   it.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipelines._hosted_api import (  # noqa: E402
    HostedApiNotAllowed,
    HostedApiPolicy,
    POLICY_RELATIVE_PATH,
    SCHEMA_PATH,
    assert_allowed,
    list_allowed_providers,
    load_policy,
)

NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _good_policy(**overrides) -> dict:
    base = {
        "schema_version": "dlrs-hosted-api-policy/1.0",
        "opt_in": True,
        "allowed_providers": ["openai", "anthropic"],
        "allowed_pipelines": ["vectorization", "moderation"],
        "consent_evidence_ref": "consent/hosted_api_consent.pointer.json",
        "issued_at": "2026-04-01T00:00:00Z",
        "expires_at": "2027-04-01T00:00:00Z",
        "data_residency": "EU only",
        "notes": "reviewed by legal 2026-04-01",
    }
    base.update(overrides)
    return base


def _seed(tmp: Path, policy: dict) -> Path:
    record = tmp / "rec"
    (record / "policy").mkdir(parents=True, exist_ok=True)
    (record / "manifest.json").write_text(
        json.dumps({"record_id": "dlrs_hostedapi_lin"}), encoding="utf-8"
    )
    (record / POLICY_RELATIVE_PATH).write_text(
        json.dumps(policy), encoding="utf-8"
    )
    return record


def _schema_golden(errors: list[str]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    # Positive: representative valid policy.
    good = _good_policy()
    for err in validator.iter_errors(good):
        errors.append(f"schema/golden: valid policy rejected: {err.message}")
        break

    # Negative cases.
    bad_cases = [
        ("missing schema_version", {**good, "schema_version": None}),
        ("schema_version drifted", {**good, "schema_version": "dlrs-hosted-api-policy/0.9"}),
        ("unknown provider", {**good, "allowed_providers": ["openai", "warpdrive_ai"]}),
        ("uppercase pipeline name", {**good, "allowed_pipelines": ["Vectorization"]}),
        ("opt_in not bool", {**good, "opt_in": "yes"}),
        ("missing consent_evidence_ref", {k: v for k, v in good.items() if k != "consent_evidence_ref"}),
        ("additional property", {**good, "secret_field": "no"}),
    ]
    for label, doc in bad_cases:
        if next(validator.iter_errors(doc), None) is None:
            errors.append(f"schema/golden: bad case '{label}' unexpectedly accepted")


def _default_deny_no_file(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        record.mkdir()
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=NOW)
        except HostedApiNotAllowed as exc:
            _assert(
                "no hosted-API policy" in str(exc),
                f"default-deny: unexpected error message: {exc!s}",
                errors,
            )
            return
        errors.append("default-deny: assert_allowed must raise when no policy file exists")


def _opt_in_false_denies(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_policy(opt_in=False))
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=NOW)
        except HostedApiNotAllowed as exc:
            _assert(
                "opt_in=false" in str(exc),
                f"opt_in=false: unexpected message: {exc!s}",
                errors,
            )
            return
        errors.append("opt_in=false: must raise even with everything else valid")


def _provider_whitelist(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_policy(allowed_providers=["anthropic"]))
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=NOW)
        except HostedApiNotAllowed as exc:
            _assert(
                "not in allowed_providers" in str(exc),
                f"provider-whitelist: unexpected message: {exc!s}",
                errors,
            )
            return
        errors.append("provider-whitelist: openai must be denied when only anthropic is allowed")


def _pipeline_whitelist(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_policy(allowed_pipelines=["moderation"]))
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=NOW)
        except HostedApiNotAllowed as exc:
            _assert(
                "not in allowed_pipelines" in str(exc),
                f"pipeline-whitelist: unexpected message: {exc!s}",
                errors,
            )
            return
        errors.append(
            "pipeline-whitelist: vectorization must be denied when only moderation is allowed"
        )


def _time_bounds(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_policy())

        # Before issued_at
        too_early = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=too_early)
        except HostedApiNotAllowed as exc:
            _assert(
                "not yet active" in str(exc),
                f"time-bounds/early: unexpected message: {exc!s}",
                errors,
            )
        else:
            errors.append("time-bounds/early: must raise before issued_at")

        # After expires_at
        too_late = datetime(2027, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        try:
            assert_allowed(record, pipeline_name="vectorization", provider="openai", now=too_late)
        except HostedApiNotAllowed as exc:
            _assert(
                "expired" in str(exc),
                f"time-bounds/late: unexpected message: {exc!s}",
                errors,
            )
        else:
            errors.append("time-bounds/late: must raise after expires_at")


def _expires_before_issued_invalid(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad = _good_policy(
            issued_at="2026-04-01T00:00:00Z",
            expires_at="2026-04-01T00:00:00Z",  # equal -> invalid
        )
        record = _seed(Path(tmp), bad)
        try:
            load_policy(record)
        except HostedApiNotAllowed as exc:
            _assert(
                "expires_at" in str(exc),
                f"expires<=issued: unexpected message: {exc!s}",
                errors,
            )
            return
        errors.append(
            "expires<=issued: load_policy must raise when expires_at <= issued_at"
        )


def _successful_gate(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_policy())
        try:
            policy = assert_allowed(
                record, pipeline_name="vectorization", provider="openai", now=NOW
            )
        except HostedApiNotAllowed as exc:
            errors.append(f"successful-gate: unexpectedly denied: {exc!s}")
            return
        _assert(
            isinstance(policy, HostedApiPolicy),
            "successful-gate: must return a HostedApiPolicy",
            errors,
        )
        _assert(
            policy.opt_in is True,
            "successful-gate: returned policy must have opt_in=True",
            errors,
        )
        _assert(
            policy.data_residency == "EU only",
            f"successful-gate: data_residency mismatch: {policy.data_residency!r}",
            errors,
        )
        _assert(
            list_allowed_providers(policy) == ["openai", "anthropic"],
            f"successful-gate: list_allowed_providers mismatch: "
            f"{list_allowed_providers(policy)!r}",
            errors,
        )

        # covers() consistency
        _assert(
            policy.covers(provider="openai", pipeline_name="vectorization", now=NOW),
            "successful-gate: covers() must agree with assert_allowed()",
            errors,
        )
        _assert(
            not policy.covers(provider="cohere", pipeline_name="vectorization", now=NOW),
            "successful-gate: covers() must reject providers outside allowed_providers",
            errors,
        )


def _malformed_json_raises(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        (record / "policy").mkdir(parents=True)
        (record / POLICY_RELATIVE_PATH).write_text("{ not valid json", encoding="utf-8")
        try:
            load_policy(record)
        except HostedApiNotAllowed as exc:
            _assert(
                "unreadable" in str(exc),
                f"malformed-json: unexpected message: {exc!s}",
                errors,
            )
            return
        errors.append("malformed-json: load_policy must raise on parse error")


def _list_allowed_providers_when_disabled(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed(Path(tmp), _good_providers := _good_policy(opt_in=False))
        policy = load_policy(record)
        _assert(
            list_allowed_providers(policy) == [],
            f"list-allowed/disabled: must be empty when opt_in=False, got "
            f"{list_allowed_providers(policy)!r}",
            errors,
        )
    _assert(
        list_allowed_providers(None) == [],
        f"list-allowed/none: must be empty for None policy, got "
        f"{list_allowed_providers(None)!r}",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    print("test_hosted_api_policy: schema/golden")
    _schema_golden(errors)
    print("test_hosted_api_policy: default-deny when no policy file")
    _default_deny_no_file(errors)
    print("test_hosted_api_policy: opt_in=false short-circuits")
    _opt_in_false_denies(errors)
    print("test_hosted_api_policy: provider whitelist")
    _provider_whitelist(errors)
    print("test_hosted_api_policy: pipeline whitelist")
    _pipeline_whitelist(errors)
    print("test_hosted_api_policy: time bounds")
    _time_bounds(errors)
    print("test_hosted_api_policy: expires_at <= issued_at invalid")
    _expires_before_issued_invalid(errors)
    print("test_hosted_api_policy: successful gate returns policy")
    _successful_gate(errors)
    print("test_hosted_api_policy: malformed JSON raises")
    _malformed_json_raises(errors)
    print("test_hosted_api_policy: list_allowed_providers when disabled / None")
    _list_allowed_providers_when_disabled(errors)

    if errors:
        print("\ntest_hosted_api_policy: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("\ntest_hosted_api_policy: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
