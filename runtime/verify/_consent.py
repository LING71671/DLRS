"""Stage 1.6 — Consent + withdrawal pre-flight.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.5.

Two responsibilities:

1. ``consent_evidence_ref`` MUST be readable. v0.9 supports
   in-archive references (``consent/...``) and same-archive paths
   only; external URIs are deferred to v0.10 once the federation
   appendix lands.
2. The withdrawal endpoint MUST be polled at session start. By default
   the runtime issues an HTTP GET; the body MUST parse to a JSON object
   whose ``status`` is anything other than ``"withdrawn"``.

For testing / offline evaluation the caller may pass a non-default
``WithdrawalPolicy`` that short-circuits the HTTP call. ``offline``
mode is rejected unless the issuer's consent document explicitly
opted into offline operation; this gate is delegated to v0.10's
consent-document parser. v0.9 only supports the test-side mock policy
``mock-…`` which is forbidden in production builds.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any, Literal

from runtime.verify.result import VerifyResult


WithdrawalMode = Literal[
    "online",
    "mock-not-revoked",
    "mock-revoked",
    "mock-unreachable",
    "mock-malformed",
]


@dataclass(frozen=True)
class WithdrawalPolicy:
    """How to evaluate ``life-package.withdrawal_endpoint`` at Stage 1.

    ``mode == "online"`` (default): real HTTP GET, follow the spec.
    ``mode.startswith("mock-")``: test-only short-circuit.
    """

    mode: WithdrawalMode = "online"
    timeout_seconds: float = 10.0

    def is_mock(self) -> bool:
        return self.mode.startswith("mock-")


def verify_consent_readable(
    zf: zipfile.ZipFile,
    descriptor: dict[str, Any],
    vr: VerifyResult,
) -> bool:
    ref = descriptor.get("consent_evidence_ref")
    if not isinstance(ref, str) or not ref:
        vr.add_error("consent", "consent_evidence_ref_missing")
        return False

    parsed = urllib.parse.urlparse(ref)
    if parsed.scheme and parsed.scheme not in ("file",):
        vr.add_error(
            "consent",
            "external_consent_uri_not_supported_at_v0_9",
            ref,
        )
        return False

    candidate = ref
    if parsed.scheme == "file":
        candidate = parsed.path.lstrip("/")
    try:
        data = zf.read(candidate)
    except KeyError:
        vr.add_error("consent", "consent_evidence_ref_unreadable", ref)
        return False
    if not data:
        vr.add_error("consent", "consent_evidence_empty", ref)
        return False
    return True


def _interpret_response(body: bytes, vr: VerifyResult) -> bool:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        vr.add_error("withdrawal", "response_not_utf8", str(exc))
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        vr.add_error("withdrawal", "response_not_json", str(exc))
        return False
    if not isinstance(parsed, dict):
        vr.add_error("withdrawal", "response_not_object")
        return False
    status = parsed.get("status")
    if status == "withdrawn":
        vr.add_error("withdrawal", "package_withdrawn")
        return False
    return True


def poll_withdrawal_endpoint(
    descriptor: dict[str, Any],
    policy: WithdrawalPolicy,
    vr: VerifyResult,
    audit_emit: Any | None = None,
) -> bool:
    """Issue the §2.5 step-2 pre-flight poll.

    On success returns ``True`` and emits a ``withdrawal_poll`` audit
    event with ``result="not_revoked"``. On any failure returns
    ``False`` and emits the same audit event with the appropriate
    ``result`` string.
    """

    endpoint = descriptor.get("withdrawal_endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        vr.add_error("withdrawal", "withdrawal_endpoint_missing")
        return False

    if policy.mode == "mock-not-revoked":
        if audit_emit:
            audit_emit("withdrawal_poll", endpoint=endpoint, result="not_revoked")
        return True
    if policy.mode == "mock-revoked":
        if audit_emit:
            audit_emit("withdrawal_poll", endpoint=endpoint, result="revoked")
        vr.add_error("withdrawal", "package_withdrawn")
        return False
    if policy.mode == "mock-unreachable":
        if audit_emit:
            audit_emit("withdrawal_poll", endpoint=endpoint, result="unreachable")
        vr.add_error("withdrawal", "endpoint_unreachable", "(mock)")
        return False
    if policy.mode == "mock-malformed":
        if audit_emit:
            audit_emit("withdrawal_poll", endpoint=endpoint, result="malformed")
        vr.add_error("withdrawal", "response_not_json", "(mock)")
        return False

    # Real HTTP GET path (default). Construct the Request defensively —
    # urllib raises ``ValueError("unknown url type")`` for schemeless URLs,
    # which the descriptor schema does not currently reject.
    try:
        req = urllib.request.Request(
            endpoint,
            method="GET",
            headers={"User-Agent": "lifectl/0.9"},
        )
    except ValueError as exc:
        if audit_emit:
            audit_emit(
                "withdrawal_poll",
                endpoint=endpoint,
                result="malformed_url",
            )
        vr.add_error("withdrawal", "endpoint_malformed_url", str(exc))
        return False
    try:
        with urllib.request.urlopen(req, timeout=policy.timeout_seconds) as resp:
            status_code = getattr(resp, "status", 200)
            body = resp.read()
    except urllib.error.HTTPError as exc:
        if audit_emit:
            audit_emit(
                "withdrawal_poll",
                endpoint=endpoint,
                result="unreachable",
                http_status=exc.code,
            )
        vr.add_error(
            "withdrawal",
            "endpoint_http_error",
            f"{endpoint} -> HTTP {exc.code}",
        )
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if audit_emit:
            audit_emit("withdrawal_poll", endpoint=endpoint, result="unreachable")
        vr.add_error("withdrawal", "endpoint_unreachable", str(exc))
        return False

    if status_code >= 400:
        if audit_emit:
            audit_emit(
                "withdrawal_poll",
                endpoint=endpoint,
                result="unreachable",
                http_status=status_code,
            )
        vr.add_error(
            "withdrawal",
            "endpoint_http_error",
            f"{endpoint} -> HTTP {status_code}",
        )
        return False

    if not _interpret_response(body, vr):
        if audit_emit:
            audit_emit(
                "withdrawal_poll",
                endpoint=endpoint,
                result="malformed_or_revoked",
                http_status=status_code,
            )
        return False

    if audit_emit:
        audit_emit(
            "withdrawal_poll",
            endpoint=endpoint,
            result="not_revoked",
            http_status=status_code,
        )
    return True
