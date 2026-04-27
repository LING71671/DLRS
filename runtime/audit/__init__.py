"""Runtime-side audit emitter.

v0.9 sub-issue #121 lands the *recorder* surface used by Stages 1-4
(``AuditRecorder.emit(event_type, **fields)``). The full v0.4 hash-chain
implementation that links the runtime's session log back to the bundled
``audit/events.jsonl`` chain ships in v0.9 sub-issue #125 (Stage 5 Guard);
until then events are accumulated in memory and optionally written to a
JSONL file for inspection / test assertions.
"""

from __future__ import annotations

from runtime.audit.recorder import AuditRecorder, AuditEvent

__all__ = ["AuditRecorder", "AuditEvent"]
