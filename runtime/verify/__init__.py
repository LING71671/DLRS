"""Stage 1 — Verify (sub-issue #121).

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.1-§2.5 (v0.7 load sequence)
plus v0.8 Part B §B.1 row 1 (lifecycle gate + withdrawal pre-flight +
audit-chain integrity).

Public surface::

    from runtime.verify import verify, VerifyResult, WithdrawalPolicy
    result = verify(life_path, audit=recorder, withdrawal_policy=...)

The ``verify`` function executes seven sub-steps in order. The first
failure aborts, emits an ``assembly_aborted{stage="verify", reason}``
audit event (when an audit recorder is supplied), and returns the
``VerifyResult`` with ``ok=False`` so the caller can present a
structured rejection to the user.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.verify._audit_chain import verify_audit_chain
from runtime.verify._consent import (
    WithdrawalPolicy,
    poll_withdrawal_endpoint,
    verify_consent_readable,
)
from runtime.verify._inventory import verify_inventory
from runtime.verify._lifecycle import gate_lifecycle
from runtime.verify._schema import (
    validate_descriptor,
    validate_forbidden_uses_namespace,
)
from runtime.verify._structural import open_archive, parse_descriptor
from runtime.verify._time import check_time_bounds
from runtime.verify.result import VerifyError, VerifyResult


__all__ = [
    "verify",
    "VerifyResult",
    "VerifyError",
    "WithdrawalPolicy",
]


def _abort(vr: VerifyResult, audit: Any | None) -> VerifyResult:
    if audit is not None and vr.errors:
        first = vr.first_error()
        audit.emit(
            "assembly_aborted",
            stage="verify",
            reason=first.reason if first else "unknown",
            step=first.step if first else None,
            detail=first.detail if first else None,
        )
    return vr


def verify(
    life_path: str | Path,
    *,
    audit: Any | None = None,
    withdrawal_policy: WithdrawalPolicy | None = None,
) -> VerifyResult:
    """Run Stage 1 Verify against ``life_path``.

    ``audit`` should be a ``runtime.audit.AuditRecorder`` (or any object
    with a compatible ``emit(event_type, **fields)`` method). Pass
    ``None`` to skip emission entirely (only in tests / introspection
    flows).

    ``withdrawal_policy`` defaults to ``WithdrawalPolicy(mode="online")``
    which performs a real HTTP GET. Tests use ``mock-…`` modes.
    """

    path = Path(life_path)
    policy = withdrawal_policy or WithdrawalPolicy()

    vr = VerifyResult(ok=True, life_path=path)

    if audit is not None:
        audit.emit(
            "mount_attempted",
            life_path=str(path),
            stage_about_to_run="verify",
        )

    zf = open_archive(path, vr)
    if zf is None:
        return _abort(vr, audit)

    try:
        descriptor = parse_descriptor(zf, vr)
        if descriptor is None:
            return _abort(vr, audit)

        if not validate_descriptor(descriptor, vr):
            return _abort(vr, audit)
        if not validate_forbidden_uses_namespace(vr):
            return _abort(vr, audit)

        if not check_time_bounds(vr):
            return _abort(vr, audit)

        if not verify_inventory(zf, descriptor, vr):
            return _abort(vr, audit)

        if not verify_audit_chain(zf, descriptor, vr):
            return _abort(vr, audit)

        if not verify_consent_readable(zf, descriptor, vr):
            return _abort(vr, audit)

        emit = audit.emit if audit is not None else None
        if not poll_withdrawal_endpoint(descriptor, policy, vr, audit_emit=emit):
            return _abort(vr, audit)

        if not gate_lifecycle(zf, vr):
            return _abort(vr, audit)
    finally:
        zf.close()

    return vr
