#!/usr/bin/env python3
"""Append an audit event to a DLRS record's audit/events.jsonl.

The events file is intended as an append-only journal: each line is one
JSON object that conforms to schemas/audit-event.schema.json. This tool
enforces hash chaining and refuses to rewrite history; it never deletes
or rewrites prior lines.

Example:
    python tools/emit_audit_event.py \
        --record humans/asia/cn/dlrs_94f1c9b8_lin-example \
        --event consent_verified \
        --actor-role platform_reviewer \
        --actor-id reviewer-42 \
        --reason "Consent video reviewed and approved" \
        --evidence-ref consent/consent_video.pointer.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - dep installed via tools/requirements.txt
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "audit-event.schema.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical_dump(obj: dict) -> str:
    """Stable JSON serialization for hashing: sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_manifest(record_dir: Path) -> dict:
    manifest_path = record_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest.json not found under {record_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def read_last_event(events_path: Path) -> dict | None:
    if not events_path.exists():
        return None
    last = None
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        return None
    return json.loads(last)


def existing_event_ids(events_path: Path) -> set[str]:
    if not events_path.exists():
        return set()
    ids = set()
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["event_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def build_event(args, record_id: str, prev_hash: str | None) -> dict:
    metadata = {}
    for kv in args.metadata or []:
        if "=" not in kv:
            raise SystemExit(f"--metadata expects key=value, got {kv!r}")
        k, v = kv.split("=", 1)
        metadata[k] = v
    payload: dict = {
        "event_id": args.event_id or uuid.uuid4().hex,
        "event_type": args.event,
        "record_id": record_id,
        "actor_role": args.actor_role,
        "actor_id": args.actor_id,
        "timestamp": args.timestamp or utc_now_iso(),
        "reason": args.reason,
        "evidence_ref": args.evidence_ref,
        "prev_hash": prev_hash,
    }
    if metadata:
        payload["metadata"] = metadata
    # Drop optional Nones except prev_hash (allowed null per schema).
    for k in list(payload.keys()):
        if payload[k] is None and k not in {"prev_hash", "actor_id", "evidence_ref"}:
            del payload[k]
    payload["hash"] = sha256_of(canonical_dump({k: v for k, v in payload.items() if k != "hash"}))
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description="Append an audit event to a record's events.jsonl")
    p.add_argument("--record", required=True, help="Path to the record directory containing manifest.json")
    p.add_argument("--event", required=True, help="Event type (see schemas/audit-event.schema.json)")
    p.add_argument("--actor-role", required=True, help="Role of the actor emitting the event")
    p.add_argument("--actor-id", default=None, help="Opaque actor identifier")
    p.add_argument("--reason", required=True, help="Short human-readable reason")
    p.add_argument("--evidence-ref", default=None, help="Optional pointer to supporting evidence")
    p.add_argument("--metadata", action="append", default=[], help="Repeatable key=value metadata")
    p.add_argument("--timestamp", default=None, help="ISO-8601 timestamp; defaults to now (UTC)")
    p.add_argument("--event-id", default=None, help="Override event_id; defaults to a fresh UUID4 hex")
    p.add_argument("--events-file", default="audit/events.jsonl", help="Path inside the record dir to append to")
    p.add_argument("--dry-run", action="store_true", help="Do not write; print the event to stdout")
    args = p.parse_args()

    record_dir = Path(args.record).resolve()
    manifest = load_manifest(record_dir)
    record_id = manifest["record_id"]

    events_path = record_dir / args.events_file
    events_path.parent.mkdir(parents=True, exist_ok=True)
    last = read_last_event(events_path)
    prev_hash = last["hash"] if last else None
    if last and "timestamp" in last and args.timestamp:
        if args.timestamp < last["timestamp"]:
            raise SystemExit("--timestamp must be >= previous event timestamp; events are append-only")

    event = build_event(args, record_id, prev_hash)

    if event["event_id"] in existing_event_ids(events_path):
        raise SystemExit(f"event_id {event['event_id']} already exists; refusing to rewrite history")

    if jsonschema is not None:
        jsonschema.Draft202012Validator(load_schema()).validate(event)

    line = canonical_dump(event)
    if args.dry_run:
        print(line)
        return 0
    with events_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"wrote event_id={event['event_id']} to {events_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
