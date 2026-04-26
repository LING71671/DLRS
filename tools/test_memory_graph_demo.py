#!/usr/bin/env python3
"""End-to-end test for examples/memory-graph-demo.

Runs ``examples/memory-graph-demo/run_demo.sh`` against a *temporary
copy* of the example so the in-repo example tree stays clean (the
``derived/`` and ``audit/`` outputs are gitignored but the test still
mustn't depend on local state). After the run, asserts that every
expected artefact exists, every descriptor validates against
``schemas/derived-asset.schema.json``, the audit log contains exactly
three hash-chained ``derived_asset_emitted`` events (one per pipeline),
and each descriptor's ``audit_event_ref`` matches its corresponding
audit-log line.

The test uses only the deterministic backends (``paragraph`` atomiser,
``regex`` extractor) so it stays offline-first and runs in <2s with no
model download.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
DEMO_SOURCE = ROOT / "examples" / "memory-graph-demo"
DERIVED_SCHEMA = ROOT / "schemas" / "derived-asset.schema.json"
AUDIT_SCHEMA = ROOT / "schemas" / "audit-event.schema.json"

EXPECTED_ARTEFACTS = [
    "derived/text/diary.clean.txt",
    "derived/text/diary.redactions.json",
    "derived/text/diary.clean.descriptor.json",
    "derived/memory_atoms/diary.atoms.jsonl",
    "derived/memory_atoms/diary.atoms.descriptor.json",
    "derived/knowledge_graph/diary.nodes.jsonl",
    "derived/knowledge_graph/diary.edges.jsonl",
    "derived/knowledge_graph/diary.graph.descriptor.json",
]

DESCRIPTORS_TO_AUDIT_LINES = {
    "derived/text/diary.clean.descriptor.json": ("text", "audit/events.jsonl#L1"),
    "derived/memory_atoms/diary.atoms.descriptor.json": ("memory_atoms", "audit/events.jsonl#L2"),
    "derived/knowledge_graph/diary.graph.descriptor.json": ("knowledge_graph", "audit/events.jsonl#L3"),
}


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _copy_demo(tmp_root: Path) -> Path:
    dest = tmp_root / "memory-graph-demo"
    shutil.copytree(
        DEMO_SOURCE,
        dest,
        ignore=shutil.ignore_patterns("derived", "audit"),
    )
    return dest


def _run_demo(demo_dir: Path, errors: list[str]) -> bool:
    import os

    env = os.environ.copy()
    env["DLRS_REPO_ROOT"] = str(ROOT)
    proc = subprocess.run(
        ["bash", str(demo_dir / "run_demo.sh")],
        cwd=str(demo_dir),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        errors.append(
            f"run_demo.sh exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
        return False
    return True


def _validate_descriptor(descriptor_path: Path, errors: list[str]) -> dict:
    schema = json.loads(DERIVED_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    for err in validator.iter_errors(descriptor):
        errors.append(
            f"descriptor {descriptor_path.name} fails schema: {err.message}"
        )
        break
    return descriptor


def _validate_audit_chain(demo_dir: Path, errors: list[str]) -> list[dict]:
    events_path = demo_dir / "audit" / "events.jsonl"
    if not events_path.exists():
        errors.append(f"audit chain: missing {events_path}")
        return []
    schema = json.loads(AUDIT_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    events: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))

    _assert(
        len(events) == 3,
        f"audit chain: expected 3 events, got {len(events)}",
        errors,
    )

    expected_pipelines = ["text", "memory_atoms", "knowledge_graph"]
    for idx, event in enumerate(events):
        for err in validator.iter_errors(event):
            errors.append(
                f"audit chain: event L{idx + 1} fails schema: {err.message}"
            )
            break
        _assert(
            event.get("event_type") == "derived_asset_emitted",
            f"audit chain: event L{idx + 1} type mismatch: {event.get('event_type')!r}",
            errors,
        )
        if idx < len(expected_pipelines):
            _assert(
                event.get("metadata", {}).get("pipeline") == expected_pipelines[idx],
                f"audit chain: event L{idx + 1} pipeline mismatch: "
                f"{event.get('metadata', {}).get('pipeline')!r} != "
                f"{expected_pipelines[idx]!r}",
                errors,
            )
        if idx == 0:
            _assert(
                event.get("prev_hash") is None,
                f"audit chain: genesis event prev_hash must be null, got "
                f"{event.get('prev_hash')!r}",
                errors,
            )
        else:
            _assert(
                event.get("prev_hash") == events[idx - 1].get("hash"),
                f"audit chain: event L{idx + 1} prev_hash {event.get('prev_hash')!r} "
                f"does not match previous event hash {events[idx - 1].get('hash')!r}",
                errors,
            )
    return events


def _validate_descriptor_back_fills(demo_dir: Path, errors: list[str]) -> None:
    for rel, (pipeline_name, expected_ref) in DESCRIPTORS_TO_AUDIT_LINES.items():
        descriptor_path = demo_dir / rel
        if not descriptor_path.exists():
            errors.append(f"backfill: missing descriptor {rel}")
            continue
        descriptor = _validate_descriptor(descriptor_path, errors)
        _assert(
            descriptor.get("pipeline") == pipeline_name,
            f"backfill: descriptor {rel}.pipeline mismatch "
            f"({descriptor.get('pipeline')!r} != {pipeline_name!r})",
            errors,
        )
        _assert(
            descriptor.get("audit_event_ref") == expected_ref,
            f"backfill: descriptor {rel}.audit_event_ref mismatch "
            f"({descriptor.get('audit_event_ref')!r} != {expected_ref!r})",
            errors,
        )


def main() -> int:
    if not DEMO_SOURCE.is_dir():
        print(
            f"test_memory_graph_demo: examples/memory-graph-demo not found at {DEMO_SOURCE}",
            file=sys.stderr,
        )
        return 2

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        demo_dir = _copy_demo(Path(tmp))
        if not _run_demo(demo_dir, errors):
            for err in errors:
                print(f"  - {err}")
            return 1

        for rel in EXPECTED_ARTEFACTS:
            artefact = demo_dir / rel
            _assert(artefact.exists(), f"missing artefact: {rel}", errors)

        _validate_descriptor_back_fills(demo_dir, errors)
        _validate_audit_chain(demo_dir, errors)

    if errors:
        print("test_memory_graph_demo: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        f"test_memory_graph_demo: {len(EXPECTED_ARTEFACTS)} artefacts written, "
        f"{len(DESCRIPTORS_TO_AUDIT_LINES)} descriptors validated, audit chain OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
