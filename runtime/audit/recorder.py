"""Lightweight in-memory audit recorder used until v0.9 sub-issue #125.

This is **not** the v0.4 hash-chain emitter — that lands in #125 and will
take over both responsibilities of recording AND of chaining
``prev_hash`` from the bundled ``audit/events.jsonl`` tip.

For Stage 1 Verify (sub-issue #121) the runtime needs a way to record
``mount_attempted``, ``withdrawal_poll``, and ``assembly_aborted`` events
deterministically so tests can assert on them. The recorder accumulates
events in order and optionally mirrors them to a JSONL file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class AuditEvent:
    """One recorded audit event.

    ``event_type`` matches the v0.7 / v0.8 vocabulary (e.g.
    ``mount_attempted``, ``withdrawal_poll``, ``assembly_aborted``,
    ``capability_bound``, ``lifecycle_transition_observed``, ``unmount``).
    ``occurred_at`` is the wall-clock timestamp at recording.
    ``fields`` carries per-event payload as a plain dict.
    """

    event_type: str
    occurred_at: str
    fields: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "fields": self.fields,
        }


@dataclass
class AuditRecorder:
    """Append-only ordered list of audit events.

    Pass ``mirror_path`` to also stream each event to a JSONL file on
    disk (used by ``lifectl info`` to produce inspectable output). The
    full hash-chained emitter from sub-issue #125 will subclass / replace
    this object while keeping the same ``emit`` API.
    """

    mirror_path: Path | None = None
    events: list[AuditEvent] = field(default_factory=list)

    def emit(self, event_type: str, **fields: Any) -> AuditEvent:
        evt = AuditEvent(
            event_type=event_type,
            occurred_at=_utc_now_iso(),
            fields=dict(fields),
        )
        self.events.append(evt)
        if self.mirror_path is not None:
            self.mirror_path.parent.mkdir(parents=True, exist_ok=True)
            with self.mirror_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(evt.to_dict(), sort_keys=True) + "\n")
        return evt

    def types(self) -> list[str]:
        return [e.event_type for e in self.events]

    def latest(self, event_type: str) -> AuditEvent | None:
        for evt in reversed(self.events):
            if evt.event_type == event_type:
                return evt
        return None


def default_mirror_path(package_id: str) -> Path:
    """Default per-mount audit log path: ``$XDG_DATA_HOME or ~/.local/share/dlrs/mounts/<pkg>/events.jsonl``."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "dlrs" / "mounts" / package_id / "events.jsonl"
