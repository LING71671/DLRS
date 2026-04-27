"""Public Stage 1 Verify result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VerifyError:
    """One verification failure.

    ``step`` is one of:

    - ``structural`` (zip open / required entries / descriptor parse)
    - ``schema`` (life-package schema or forbidden_uses key namespace)
    - ``time`` (created_at in the future / expires_at in the past)
    - ``inventory`` (missing entry / hash mismatch / unlisted entry)
    - ``audit_chain`` (prev_hash break or audit_event_ref pointer wrong)
    - ``consent`` (consent_evidence_ref unreadable)
    - ``withdrawal`` (endpoint unreachable, 4xx/5xx, or status=withdrawn)
    - ``lifecycle`` (lifecycle_state == withdrawn etc.)
    """

    step: str
    reason: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"step": self.step, "reason": self.reason}
        if self.detail is not None:
            d["detail"] = self.detail
        return d


@dataclass
class VerifyResult:
    """Full Stage 1 outcome.

    The result is *always* returned (even on failure) so the CLI / Stage
    2 caller can inspect what was verified, what was attempted, and which
    step rejected the package. Stage gating is the caller's job — Stage
    2 MUST refuse to proceed when ``ok is False``.
    """

    ok: bool
    life_path: Path
    package_id: str | None = None
    schema_version: str | None = None
    mode: str | None = None
    record_id: str | None = None
    created_at: str | None = None
    expires_at: str | None = None
    runtime_compatibility: list[str] = field(default_factory=list)
    forbidden_uses: list[str] = field(default_factory=list)
    lifecycle_state: str | None = None
    audit_chain_length: int | None = None
    audit_event_ref: str | None = None
    inventory_entries_verified: int = 0
    descriptor: dict[str, Any] | None = None
    errors: list[VerifyError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, step: str, reason: str, detail: str | None = None) -> None:
        self.errors.append(VerifyError(step=step, reason=reason, detail=detail))
        self.ok = False

    def first_error(self) -> VerifyError | None:
        return self.errors[0] if self.errors else None
