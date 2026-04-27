"""Stage 1.3 — Time-bound check.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.2 — refuse to mount after
``expires_at``. We additionally reject ``created_at`` in the future
(>30s clock skew tolerance) because that indicates either tampering or
a badly-set issuer clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from runtime.verify.result import VerifyResult


_FUTURE_SKEW_TOLERANCE = timedelta(seconds=30)


def _parse_iso(s: str) -> datetime | None:
    # The schema mandates RFC 3339 UTC. ``fromisoformat`` accepts both
    # ``Z`` (Python ≥3.11) and explicit offset; normalise both. Naive
    # datetimes (no tzinfo) violate RFC 3339 and are rejected — letting
    # them through would crash the offset-aware comparisons below.
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    return dt


def check_time_bounds(vr: VerifyResult, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    created_raw = vr.created_at
    expires_raw = vr.expires_at
    if not created_raw or not expires_raw:
        # Schema validation should have caught this; defensive only.
        vr.add_error(
            "time",
            "missing_time_fields",
            f"created_at={created_raw!r} expires_at={expires_raw!r}",
        )
        return False

    created = _parse_iso(created_raw)
    expires = _parse_iso(expires_raw)
    if created is None:
        vr.add_error("time", "created_at_unparseable", created_raw)
        return False
    if expires is None:
        vr.add_error("time", "expires_at_unparseable", expires_raw)
        return False

    if created > now + _FUTURE_SKEW_TOLERANCE:
        vr.add_error(
            "time",
            "created_at_in_future",
            f"created_at={created.isoformat()} now={now.isoformat()}",
        )
        return False

    if expires <= now:
        vr.add_error(
            "time",
            "package_expired",
            f"expires_at={expires.isoformat()} now={now.isoformat()}",
        )
        return False

    if expires <= created:
        vr.add_error(
            "time",
            "expires_before_created",
            f"created_at={created.isoformat()} expires_at={expires.isoformat()}",
        )
        return False

    return True
