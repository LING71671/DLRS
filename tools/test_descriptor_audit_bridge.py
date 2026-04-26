#!/usr/bin/env python3
"""Tests for the descriptor -> audit/events.jsonl bridge (issue #58).

What we verify:

1. **Event appended.** Running ``memory_atoms`` against a record with a
   ``manifest.json`` writes one extra ``derived_asset_emitted`` event to
   ``audit/events.jsonl``.
2. **Descriptor back-fill.** The on-disk descriptor's ``audit_event_ref``
   matches the form ``audit/events.jsonl#L<n>`` and points at the line
   that was actually appended.
3. **Hash chain.** The new event's ``prev_hash`` matches the ``hash`` of
   the immediately preceding line, exactly like ``tools/emit_audit_event.py``.
4. **Schema compliance.** The new event passes
   ``schemas/audit-event.schema.json`` validation.
5. **--no-audit silences the bridge.** Re-running the pipeline with the
   flag must NOT append a new event and must NOT mutate the descriptor's
   ``audit_event_ref``.
6. **No-manifest is silent.** Running the pipeline with ``--input`` only
   (no ``--record``) must not crash and must not invent an audit log.
7. **Multi-pipeline chain integrity.** Running ``memory_atoms`` then
   ``knowledge_graph`` against the same record produces a coherent
   chain with two new events whose ``prev_hash`` values link correctly.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "audit-event.schema.json"


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _read_events(record_root: Path) -> list[dict]:
    events_path = record_root / "audit" / "events.jsonl"
    if not events_path.exists():
        return []
    out: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _seed_record(tmp: Path, record_id: str) -> Path:
    record = tmp / "rec"
    (record / "derived" / "text").mkdir(parents=True, exist_ok=True)
    (record / "manifest.json").write_text(
        json.dumps({"record_id": record_id}), encoding="utf-8"
    )
    (record / "derived" / "text" / "sample.clean.txt").write_text(
        "Alice met Bob in Beijing.\n\n"
        "They exchanged contact details and agreed to follow up.\n\n"
        "European Commission representatives took notes throughout.",
        encoding="utf-8",
    )
    return record


def _run_memory_atoms(record: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_pipeline.py"),
        "memory_atoms",
        "--record",
        str(record),
        "--sensitivity",
        "S1_INTERNAL",
        *extra,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def _run_knowledge_graph(record: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_pipeline.py"),
        "knowledge_graph",
        "--record",
        str(record),
        "--sensitivity",
        "S1_INTERNAL",
        *extra,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def _e2e_event_appended_and_descriptor_backfilled(errors: list[str]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed_record(Path(tmp), "dlrs_bridge_lin")
        proc = _run_memory_atoms(record)
        _assert(
            proc.returncode == 0,
            f"bridge/append: cli exit {proc.returncode}\nstderr={proc.stderr}",
            errors,
        )

        events = _read_events(record)
        _assert(
            len(events) == 1,
            f"bridge/append: expected 1 audit event, got {len(events)}",
            errors,
        )
        if not events:
            return
        event = events[0]
        _assert(
            event["event_type"] == "derived_asset_emitted",
            f"bridge/append: event_type mismatch: {event.get('event_type')!r}",
            errors,
        )
        _assert(
            event["actor_role"] == "system",
            f"bridge/append: actor_role mismatch: {event.get('actor_role')!r}",
            errors,
        )
        _assert(
            event["record_id"] == "dlrs_bridge_lin",
            f"bridge/append: record_id mismatch: {event.get('record_id')!r}",
            errors,
        )
        _assert(
            event.get("prev_hash") is None,
            f"bridge/append: first event's prev_hash must be null, got {event.get('prev_hash')!r}",
            errors,
        )
        meta = event.get("metadata") or {}
        _assert(
            meta.get("pipeline") == "memory_atoms",
            f"bridge/append: metadata.pipeline mismatch: {meta.get('pipeline')!r}",
            errors,
        )
        for key in ("descriptor_path", "output_path", "outputs_hash", "pipeline_version"):
            _assert(
                isinstance(meta.get(key), str) and meta[key],
                f"bridge/append: metadata.{key} must be a non-empty string, got {meta.get(key)!r}",
                errors,
            )

        # Schema validation
        for err in validator.iter_errors(event):
            errors.append(f"bridge/append: event fails audit-event schema: {err.message}")
            break

        # Descriptor back-fill
        descriptor_path = (
            record / "derived" / "memory_atoms" / "sample.atoms.descriptor.json"
        )
        _assert(
            descriptor_path.exists(),
            f"bridge/append: descriptor missing at {descriptor_path}",
            errors,
        )
        if descriptor_path.exists():
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            ref = descriptor.get("audit_event_ref")
            _assert(
                ref == "audit/events.jsonl#L1",
                f"bridge/append: audit_event_ref mismatch: {ref!r}",
                errors,
            )


def _e2e_no_audit_flag_skips_bridge(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed_record(Path(tmp), "dlrs_bridge_skip")
        proc = _run_memory_atoms(record, "--no-audit")
        _assert(
            proc.returncode == 0,
            f"bridge/skip: cli exit {proc.returncode}\nstderr={proc.stderr}",
            errors,
        )

        events_path = record / "audit" / "events.jsonl"
        _assert(
            not events_path.exists(),
            f"bridge/skip: --no-audit must NOT create audit/events.jsonl, found "
            f"{events_path.read_text(encoding='utf-8') if events_path.exists() else ''}",
            errors,
        )

        descriptor_path = (
            record / "derived" / "memory_atoms" / "sample.atoms.descriptor.json"
        )
        if descriptor_path.exists():
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            _assert(
                descriptor.get("audit_event_ref") in (None, ""),
                f"bridge/skip: --no-audit must leave audit_event_ref unset, got {descriptor.get('audit_event_ref')!r}",
                errors,
            )


def _e2e_no_manifest_is_silent(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # NO manifest.json under tmp — pipeline run via --input only.
        input_path = Path(tmp) / "free.clean.txt"
        input_path.write_text(
            "First paragraph.\n\nSecond paragraph mentions Alice.\n\nThird.",
            encoding="utf-8",
        )
        out_dir = Path(tmp) / "out"
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "memory_atoms",
            "--input",
            str(input_path),
            "--output-dir",
            str(out_dir),
            "--sensitivity",
            "S1_INTERNAL",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        _assert(
            proc.returncode == 0,
            f"bridge/no-manifest: cli exit {proc.returncode}\nstderr={proc.stderr}",
            errors,
        )

        # Pipeline must not invent audit/events.jsonl somewhere.
        for path in Path(tmp).rglob("events.jsonl"):
            errors.append(f"bridge/no-manifest: stray audit log emitted at {path}")

        descriptor_path = out_dir / "free.atoms.descriptor.json"
        if descriptor_path.exists():
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            _assert(
                descriptor.get("audit_event_ref") in (None, ""),
                f"bridge/no-manifest: descriptor must have null audit_event_ref, got "
                f"{descriptor.get('audit_event_ref')!r}",
                errors,
            )


def _e2e_chain_across_two_pipelines(errors: list[str]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    with tempfile.TemporaryDirectory() as tmp:
        record = _seed_record(Path(tmp), "dlrs_bridge_chain")
        proc1 = _run_memory_atoms(record)
        _assert(
            proc1.returncode == 0,
            f"bridge/chain: memory_atoms cli exit {proc1.returncode}\nstderr={proc1.stderr}",
            errors,
        )
        proc2 = _run_knowledge_graph(record)
        _assert(
            proc2.returncode == 0,
            f"bridge/chain: knowledge_graph cli exit {proc2.returncode}\nstderr={proc2.stderr}",
            errors,
        )

        events = _read_events(record)
        _assert(
            len(events) == 2,
            f"bridge/chain: expected 2 events, got {len(events)}",
            errors,
        )
        if len(events) != 2:
            return
        e1, e2 = events
        for event in events:
            for err in validator.iter_errors(event):
                errors.append(f"bridge/chain: event fails schema: {err.message}")
                break

        _assert(
            e1.get("metadata", {}).get("pipeline") == "memory_atoms",
            f"bridge/chain: first event must be memory_atoms, got "
            f"{e1.get('metadata', {}).get('pipeline')!r}",
            errors,
        )
        _assert(
            e2.get("metadata", {}).get("pipeline") == "knowledge_graph",
            f"bridge/chain: second event must be knowledge_graph, got "
            f"{e2.get('metadata', {}).get('pipeline')!r}",
            errors,
        )

        _assert(
            e1.get("prev_hash") is None,
            f"bridge/chain: first event prev_hash must be null, got {e1.get('prev_hash')!r}",
            errors,
        )
        _assert(
            e2.get("prev_hash") == e1.get("hash"),
            f"bridge/chain: second event prev_hash {e2.get('prev_hash')!r} "
            f"must match first event hash {e1.get('hash')!r}",
            errors,
        )

        # Both descriptors must back-fill to their respective lines.
        atoms_descriptor = json.loads(
            (record / "derived" / "memory_atoms" / "sample.atoms.descriptor.json").read_text(
                encoding="utf-8"
            )
        )
        nodes_descriptor = json.loads(
            (record / "derived" / "knowledge_graph" / "sample.graph.descriptor.json").read_text(
                encoding="utf-8"
            )
        )
        _assert(
            atoms_descriptor.get("audit_event_ref") == "audit/events.jsonl#L1",
            f"bridge/chain: atoms descriptor audit_event_ref mismatch: "
            f"{atoms_descriptor.get('audit_event_ref')!r}",
            errors,
        )
        _assert(
            nodes_descriptor.get("audit_event_ref") == "audit/events.jsonl#L2",
            f"bridge/chain: nodes descriptor audit_event_ref mismatch: "
            f"{nodes_descriptor.get('audit_event_ref')!r}",
            errors,
        )


def main() -> int:
    errors: list[str] = []
    print("test_descriptor_audit_bridge: e2e/event-appended + descriptor back-fill")
    _e2e_event_appended_and_descriptor_backfilled(errors)
    print("test_descriptor_audit_bridge: e2e/--no-audit skips bridge")
    _e2e_no_audit_flag_skips_bridge(errors)
    print("test_descriptor_audit_bridge: e2e/no-manifest is silent")
    _e2e_no_manifest_is_silent(errors)
    print("test_descriptor_audit_bridge: e2e/chain across memory_atoms + knowledge_graph")
    _e2e_chain_across_two_pipelines(errors)

    if errors:
        print("\ntest_descriptor_audit_bridge: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("\ntest_descriptor_audit_bridge: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
