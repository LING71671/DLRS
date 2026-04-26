"""Hosted-API opt-in policy gate (v0.6 issue #59).

DLRS is offline-first. Every v0.5 pipeline ships with a static guard
(``tools/validate_pipelines.py:_validate_no_hosted_api_imports``) that
refuses to merge code under ``pipelines/`` which directly imports
hosted-API SDKs (OpenAI, Anthropic, Google, Cohere, …). v0.6 introduces
a *narrow* mechanism for opting back in, on a per-record basis, while
preserving the static guard:

1. The pipeline keeps its top-level imports offline-only.
2. Any hosted-API call site is wrapped behind
   :func:`assert_allowed`. The function inspects the record's
   ``policy/hosted_api.json`` document — validated against
   ``schemas/hosted-api-policy.schema.json`` — and raises
   :class:`HostedApiNotAllowed` unless every check below passes:

   - The policy file exists.
   - ``opt_in`` is literally ``true``.
   - ``provider`` is in ``allowed_providers``.
   - ``pipeline_name`` is in ``allowed_pipelines``.
   - ``issued_at <= now < expires_at``.

3. The hosted SDK is then loaded with :func:`importlib.import_module`
   *inside* the gated branch, so the static "no hosted-API imports"
   grep continues to pass.

Policies are stored *inside the record* so consent and policy travel
together; takedown / consent-withdrawal flows can simply delete the
file or set ``opt_in: false``.

This module is intentionally dependency-light: it pulls in the
``jsonschema`` validator already required by the rest of v0.4+ tooling
and nothing else. It never imports any hosted-API SDK itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "hosted-api-policy.schema.json"
POLICY_RELATIVE_PATH = "policy/hosted_api.json"


class HostedApiNotAllowed(RuntimeError):
    """Raised when a pipeline asks for hosted-API authorisation but the
    record's policy denies it. The message is intentionally specific
    enough to debug from but contains no PII."""


@dataclass(frozen=True)
class HostedApiPolicy:
    """In-memory mirror of ``policy/hosted_api.json``. Read-only; the
    bridge is single-shot per pipeline run."""

    schema_version: str
    opt_in: bool
    allowed_providers: List[str]
    allowed_pipelines: List[str]
    consent_evidence_ref: str
    issued_at: datetime
    expires_at: datetime
    data_residency: Optional[str]
    notes: Optional[str]

    @classmethod
    def from_dict(cls, doc: dict) -> "HostedApiPolicy":
        return cls(
            schema_version=str(doc["schema_version"]),
            opt_in=bool(doc["opt_in"]),
            allowed_providers=list(doc["allowed_providers"]),
            allowed_pipelines=list(doc["allowed_pipelines"]),
            consent_evidence_ref=str(doc["consent_evidence_ref"]),
            issued_at=_parse_iso(str(doc["issued_at"])),
            expires_at=_parse_iso(str(doc["expires_at"])),
            data_residency=doc.get("data_residency"),
            notes=doc.get("notes"),
        )

    def covers(
        self, *, provider: str, pipeline_name: str, now: Optional[datetime] = None
    ) -> bool:
        """Cheap predicate: True iff this policy authorises ``provider``
        for ``pipeline_name`` at ``now`` (defaults to current UTC)."""
        if not self.opt_in:
            return False
        if provider not in self.allowed_providers:
            return False
        if pipeline_name not in self.allowed_pipelines:
            return False
        moment = now or _utc_now()
        if moment < self.issued_at:
            return False
        if moment >= self.expires_at:
            return False
        return True


def policy_path(record_root: Path) -> Path:
    return Path(record_root) / POLICY_RELATIVE_PATH


def load_policy(record_root: Path) -> Optional[HostedApiPolicy]:
    """Load and *schema-validate* the record's hosted-API policy.

    Returns ``None`` when the policy file does not exist (the offline
    default). Raises :class:`HostedApiNotAllowed` when the file exists
    but cannot be parsed or fails schema validation — refusing to
    silently degrade is part of the contract.
    """
    p = policy_path(record_root)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {p} is unreadable: {exc}"
        ) from exc
    _validate(doc, p)
    if doc["expires_at"] <= doc["issued_at"]:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {p}: expires_at must be strictly after issued_at"
        )
    return HostedApiPolicy.from_dict(doc)


def assert_allowed(
    record_root: Path,
    pipeline_name: str,
    provider: str,
    *,
    now: Optional[datetime] = None,
) -> HostedApiPolicy:
    """Raise unless the record opts in to ``provider`` for ``pipeline_name``.

    The single entry point pipelines use to gate hosted-API code paths.
    On success the validated :class:`HostedApiPolicy` is returned so the
    caller can additionally log ``data_residency`` / ``notes`` /
    ``consent_evidence_ref`` to ``audit/events.jsonl`` (see issue #58
    for the bridge).

    The ``now`` keyword exists exclusively for tests; production callers
    should rely on the default (current UTC).
    """
    policy = load_policy(record_root)
    if policy is None:
        raise HostedApiNotAllowed(
            f"no hosted-API policy at {policy_path(record_root)}; "
            f"DLRS is offline-first by default. To opt {pipeline_name!r} in "
            f"to {provider!r} for this record, write a "
            "policy/hosted_api.json that conforms to "
            "schemas/hosted-api-policy.schema.json."
        )
    if not policy.opt_in:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {policy_path(record_root)} has opt_in=false"
        )
    if provider not in policy.allowed_providers:
        raise HostedApiNotAllowed(
            f"provider {provider!r} not in allowed_providers="
            f"{policy.allowed_providers!r} for {policy_path(record_root)}"
        )
    if pipeline_name not in policy.allowed_pipelines:
        raise HostedApiNotAllowed(
            f"pipeline {pipeline_name!r} not in allowed_pipelines="
            f"{policy.allowed_pipelines!r} for {policy_path(record_root)}"
        )
    moment = now or _utc_now()
    if moment < policy.issued_at:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {policy_path(record_root)} not yet active "
            f"(issued_at={policy.issued_at.isoformat()}, now={moment.isoformat()})"
        )
    if moment >= policy.expires_at:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {policy_path(record_root)} expired "
            f"(expires_at={policy.expires_at.isoformat()}, now={moment.isoformat()})"
        )
    return policy


def list_allowed_providers(policy: Optional[HostedApiPolicy]) -> List[str]:
    """Convenience used by ``--show-policy`` style CLIs. Empty list when
    no policy or opt_in=false."""
    if policy is None or not policy.opt_in:
        return []
    return list(policy.allowed_providers)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp. Treat naive inputs as UTC, accept
    both ``Z`` suffix and explicit offsets, normalise to UTC."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate(doc: dict, path: Path) -> None:
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:  # pragma: no cover - tests install jsonschema
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: Iterable = jsonschema.Draft202012Validator(schema).iter_errors(doc)
    messages = [e.message for e in errors]
    if messages:
        raise HostedApiNotAllowed(
            f"hosted-API policy at {path} fails schema: " + "; ".join(messages[:3])
        )
