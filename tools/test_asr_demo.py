#!/usr/bin/env python3
"""End-to-end test for examples/asr-demo.

Runs ``examples/asr-demo/run_demo.sh`` against a *temporary copy* of the
example so the in-repo example tree stays clean (the ``derived/`` outputs
are gitignored but the test still mustn't depend on local state). After
the run, asserts that all nine expected artefacts exist and that every
descriptor validates against ``schemas/derived-asset.schema.json``.

The test uses only the deterministic backends (``dummy`` ASR, ``hash``
embedder, built-in moderation policy) so it stays offline-first and runs
in <2s with no model download.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_SOURCE = ROOT / "examples" / "asr-demo"
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"

EXPECTED_ARTEFACTS = [
    "derived/asr/voice_demo.transcript.json",
    "derived/asr/voice_demo.transcript.descriptor.json",
    "derived/text/voice_demo.clean.txt",
    "derived/text/voice_demo.redactions.json",
    "derived/text/voice_demo.clean.descriptor.json",
    "derived/vectorization/voice_demo.index.json",
    "derived/vectorization/voice_demo.index.descriptor.json",
    "derived/moderation/voice_demo.moderation.json",
    "derived/moderation/voice_demo.moderation.descriptor.json",
]

DESCRIPTORS = [p for p in EXPECTED_ARTEFACTS if p.endswith(".descriptor.json")]


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _copy_demo(tmp_root: Path) -> Path:
    dest = tmp_root / "asr-demo"
    shutil.copytree(DEMO_SOURCE, dest, ignore=shutil.ignore_patterns("derived"))
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
        errors.append(f"run_demo.sh exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}")
        return False
    return True


def _check_artefacts(demo_dir: Path, errors: list[str]) -> None:
    for rel in EXPECTED_ARTEFACTS:
        path = demo_dir / rel
        _assert(path.exists(), f"missing artefact: {rel}", errors)


def _check_descriptors(demo_dir: Path, errors: list[str]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.append("jsonschema not installed; install via tools/requirements.txt")
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for rel in DESCRIPTORS:
        path = demo_dir / rel
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        for e in sorted(validator.iter_errors(d), key=lambda e: e.path):
            errors.append(
                f"{rel} schema error at {'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            )
        # Pipelines that record a model (asr, vectorization) MUST declare
        # the offline-first invariant. Pipelines that don't use a model
        # (text cleaning, moderation) are allowed to omit the model block.
        model = d.get("model")
        if isinstance(model, dict):
            _assert(
                model.get("online_api_used") is False,
                f"{rel}: online_api_used not False",
                errors,
            )


def _check_transcript_text_chain(demo_dir: Path, errors: list[str]) -> None:
    """The text pipeline reads the ASR transcript; the moderation pipeline
    reads the clean text; the vectorization pipeline also reads the clean
    text. Sanity-check the chain by asserting non-empty payloads at each
    stage."""
    transcript_path = demo_dir / "derived/asr/voice_demo.transcript.json"
    clean_path = demo_dir / "derived/text/voice_demo.clean.txt"
    index_path = demo_dir / "derived/vectorization/voice_demo.index.json"
    moderation_path = demo_dir / "derived/moderation/voice_demo.moderation.json"

    if transcript_path.exists():
        t = json.loads(transcript_path.read_text(encoding="utf-8"))
        _assert(isinstance(t.get("segments"), list), "transcript.segments not a list", errors)
        _assert(t.get("backend") == "dummy", f"expected dummy backend, got {t.get('backend')!r}", errors)
    if clean_path.exists():
        _assert(len(clean_path.read_text(encoding="utf-8")) > 0, "clean.txt is empty", errors)
    if index_path.exists():
        idx = json.loads(index_path.read_text(encoding="utf-8"))
        _assert(idx.get("backend") == "hash", f"expected hash backend, got {idx.get('backend')!r}", errors)
        _assert(len(idx.get("entries", [])) >= 1, "index.entries empty", errors)
    if moderation_path.exists():
        m = json.loads(moderation_path.read_text(encoding="utf-8"))
        _assert(
            m.get("outcome") in {"pass", "flag", "block"},
            f"unexpected outcome {m.get('outcome')!r}",
            errors,
        )


def main() -> int:
    if not DEMO_SOURCE.exists():
        print(f"test_asr_demo: examples/asr-demo not found at {DEMO_SOURCE}", file=sys.stderr)
        return 1

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        demo_dir = _copy_demo(tmp_root)
        if not _run_demo(demo_dir, errors):
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        _check_artefacts(demo_dir, errors)
        _check_descriptors(demo_dir, errors)
        _check_transcript_text_chain(demo_dir, errors)

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"test_asr_demo: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("test_asr_demo: 9 artefacts written, 4 descriptors validated, chain OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
