"""Descriptor -> audit/events.jsonl bridge (v0.6 issue #58).

When a pipeline emits a derived-asset descriptor, it should also record
that emission as an entry on the record's append-only audit log so
reviewers can mechanically reconstruct *why* a derived artefact exists
and *what authorised* its production. Conversely, every descriptor
should know which audit event documents its emission.

This module exposes a single function,
:func:`emit_descriptor_audit_event`, that:

1. Reads the record's manifest to learn the ``record_id``.
2. Reads the last line of ``<record>/audit/events.jsonl`` to chain hashes.
3. Builds and validates a ``derived_asset_emitted`` event.
4. Atomically appends the event to the events file.
5. Returns an ``audit/events.jsonl#L<n>`` reference suitable for
   placement on the descriptor's ``audit_event_ref`` field.

The bridge is deliberately a *separate* module from the descriptor
emitter (:mod:`pipelines._descriptor`) so a pipeline that explicitly
wants to skip auditing (e.g. dry-run / fixture generation) can still
write descriptors without an audit log being present. Pipelines call
the bridge from their CLI entry point only when both a record root
*and* a manifest are available.

Why ``derived_asset_emitted`` is its own ``event_type`` rather than
piggy-backing on ``build_started``/``build_completed``: the canonical
v0.4 lifecycle events describe whole *records*, not individual
artefacts. A single record may produce many derived assets across
multiple pipeline runs; conflating them with the record-level lifecycle
would lose granularity in the audit log.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

# Reuse the v0.4 emitter's helpers for canonicalisation + hashing so the
# bridge cannot drift from the existing chain semantics.
import emit_audit_event as _emitter  # noqa: E402

EVENTS_RELATIVE_PATH = "audit/events.jsonl"
EVENT_TYPE = "derived_asset_emitted"
ACTOR_ROLE = "system"


def _events_file(record_root: Path) -> Path:
    return record_root / EVENTS_RELATIVE_PATH


def _line_count(path: Path) -> int:
    """Number of non-blank lines currently in the events file. Returns 0
    for missing or empty files."""
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def emit_descriptor_audit_event(
    record_root: Path,
    pipeline_name: str,
    descriptor: dict,
    descriptor_path: Path,
    actor_id: Optional[str] = None,
) -> str:
    """Append a ``derived_asset_emitted`` event for *descriptor*.

    Args:
        record_root: Absolute path to the DLRS record directory. Must
            contain a ``manifest.json`` whose ``record_id`` is used as
            the event's ``record_id``.
        pipeline_name: Pipeline that produced the descriptor (e.g.
            ``"memory_atoms"``, ``"knowledge_graph"``). Goes into the
            event metadata.
        descriptor: The descriptor dict that has already been validated
            against ``schemas/derived-asset.schema.json``. Used to copy
            output path + content hash into the event metadata so
            downstream tools can verify the artefact still matches the
            audited state.
        descriptor_path: Absolute path to the descriptor file just
            written. Stored as the event's ``evidence_ref`` so a
            reviewer can jump from the audit line straight to the
            descriptor.
        actor_id: Optional opaque identifier for the system component
            that triggered the emission (e.g. CI runner name). Defaults
            to ``"pipelines.<pipeline_name>"``.

    Returns:
        A reference of the form ``"audit/events.jsonl#L<n>"`` pointing
        to the line just appended (1-based; matches the format used by
        the v0.6 atom / node / edge schemas).

    Raises:
        FileNotFoundError: If ``record_root/manifest.json`` is missing.
        SystemExit: Propagated from the underlying emitter when schema
            validation fails or the chain cannot be extended.
    """
    record_root = Path(record_root).resolve()
    manifest = _emitter.load_manifest(record_root)
    record_id = manifest["record_id"]

    events_path = _events_file(record_root)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    last = _emitter.read_last_event(events_path)
    prev_hash = last["hash"] if last else None

    output_path = descriptor.get("output", {}).get("path", "")
    outputs_hash = descriptor.get("output", {}).get("outputs_hash", "")
    pipeline_version = descriptor.get("pipeline_version", "")

    try:
        descriptor_rel = str(descriptor_path.resolve().relative_to(record_root))
    except ValueError:
        descriptor_rel = descriptor_path.name

    metadata = {
        "pipeline": pipeline_name,
        "pipeline_version": pipeline_version,
        "descriptor_path": descriptor_rel,
        "output_path": output_path,
        "outputs_hash": outputs_hash,
    }

    payload = {
        "event_id": _emitter.uuid.uuid4().hex,
        "event_type": EVENT_TYPE,
        "record_id": record_id,
        "actor_role": ACTOR_ROLE,
        "actor_id": actor_id or f"pipelines.{pipeline_name}",
        "timestamp": _emitter.utc_now_iso(),
        "reason": f"derived asset emitted by pipeline {pipeline_name}",
        "evidence_ref": descriptor_rel,
        "prev_hash": prev_hash,
        "metadata": metadata,
    }
    payload["hash"] = _emitter.sha256_of(
        _emitter.canonical_dump({k: v for k, v in payload.items() if k != "hash"})
    )

    _validate(payload)

    if payload["event_id"] in _emitter.existing_event_ids(events_path):
        # Astronomically unlikely (uuid4 collision) but the chain rule
        # forbids rewriting; fall back to a fresh id and retry once.
        payload["event_id"] = _emitter.uuid.uuid4().hex
        payload.pop("hash")
        payload["hash"] = _emitter.sha256_of(
            _emitter.canonical_dump({k: v for k, v in payload.items() if k != "hash"})
        )
        _validate(payload)

    line = _emitter.canonical_dump(payload)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    line_no = _line_count(events_path)
    return f"{EVENTS_RELATIVE_PATH}#L{line_no}"


def _validate(event: dict) -> None:
    try:
        import jsonschema  # noqa: WPS433
    except ImportError:  # pragma: no cover - tests install jsonschema
        return
    schema = _emitter.load_schema()
    jsonschema.Draft202012Validator(schema).validate(event)


def update_descriptor_with_audit_ref(descriptor_path: Path, audit_ref: str) -> None:
    """Re-write *descriptor_path* with ``audit_event_ref`` populated.

    Used by callers that want the descriptor to point back at the audit
    line. Does NOT recompute any output hash — the descriptor is the
    *only* file mutated by this back-fill, and its own hash is not
    self-referential.
    """
    data = json.loads(descriptor_path.read_text(encoding="utf-8"))
    data["audit_event_ref"] = audit_ref
    descriptor_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def manifest_present(record_root: Optional[Path]) -> bool:
    """Cheap predicate used by pipeline CLIs to decide whether to call
    the bridge at all. Returns False for ``None`` and for record roots
    without a manifest (test fixtures, dry-runs)."""
    if record_root is None:
        return False
    return (Path(record_root) / "manifest.json").exists()


def maybe_bridge(
    record_root: Optional[Path],
    pipeline_name: str,
    descriptor: dict,
    descriptor_path: Path,
    skip: bool = False,
) -> Optional[str]:
    """Best-effort wrapper for pipeline CLIs.

    Performs no-op if ``skip`` is True, the record root is ``None``, or
    the record has no ``manifest.json`` (typical for test fixtures and
    output-dir-only invocations). On success, appends the audit event
    AND back-fills the descriptor's ``audit_event_ref`` so the
    descriptor file on disk reflects the post-audit state.

    Returns the audit reference, or ``None`` when the bridge was
    skipped.
    """
    if skip:
        return None
    if not manifest_present(record_root):
        return None
    audit_ref = emit_descriptor_audit_event(
        record_root=Path(record_root),
        pipeline_name=pipeline_name,
        descriptor=descriptor,
        descriptor_path=descriptor_path,
    )
    update_descriptor_with_audit_ref(descriptor_path, audit_ref)
    return audit_ref
