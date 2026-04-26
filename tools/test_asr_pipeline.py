#!/usr/bin/env python3
"""End-to-end test for the ASR pipeline using the deterministic dummy backend.

Why dummy:

- CI must stay offline-first. We do not want to download a Whisper model
  on every push.
- The point of the test is the pipeline plumbing (input resolution,
  transcript schema, descriptor schema, atomic write), NOT the quality of
  the actual speech recognition.

The real faster-whisper backend is exercised via ``examples/asr-demo``
(issue #37) and via local manual smoke tests; documenting that path in
``docs/PIPELINE_GUIDE.md`` is tracked in issue #38.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _make_synthetic_record(root: Path, *, manifest_artifacts: list[dict] | None = None) -> Path:
    """Lay down a minimal record tree the ASR pipeline can run against.

    ``manifest_artifacts`` lets individual cases exercise edge shapes
    (missing ``path`` key, pointer-style ``storage_uri`` entries, …).
    """
    record = root / "dlrs_test_asr_001"
    audio_dir = record / "artifacts" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "voice_master.wav"
    # 44 bytes of synthetic WAV header + filler. The dummy backend never
    # decodes audio, it only sha256s the file, so the contents are arbitrary.
    audio_path.write_bytes(b"RIFF" + b"\x00" * 40)

    if manifest_artifacts is None:
        manifest_artifacts = [
            {"kind": "audio", "path": "artifacts/audio/voice_master.wav"}
        ]

    manifest = {
        "schema_version": "dlrs-manifest/1.0",
        "record_id": "dlrs_test_asr_001",
        "created_at": "2026-04-26T06:00:00Z",
        "artifacts": manifest_artifacts,
    }
    (record / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return record


def _run_pipeline(
    record: Path,
    *,
    input_arg: str | None = None,
    output_dir: Path | None = None,
    cwd: Path | None = None,
) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_pipeline.py"),
        "asr",
        "--record",
        str(record),
        "--backend",
        "dummy",
        "--language",
        "zh",
    ]
    if input_arg is not None:
        cmd.extend(["--input", input_arg])
    if output_dir is not None:
        cmd.extend(["--output-dir", str(output_dir)])
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return proc.returncode
    return 0


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        record = _make_synthetic_record(tmp_root)

        # Case A: only --record (manifest auto-discovery)
        rc = _run_pipeline(record)
        _assert(rc == 0, f"run_pipeline.py asr (auto-discovery) exited with {rc}", errors)

        # Case B (regression for the relative --input bug fixed in this PR):
        # pass --input as a record-relative path while running the CLI from
        # an unrelated CWD. Before the fix, .resolve() turned the relative
        # path into $CWD/artifacts/audio/voice_master.wav and the lookup failed.
        shutil.rmtree(record / "derived", ignore_errors=True)
        rc = _run_pipeline(
            record,
            input_arg="artifacts/audio/voice_master.wav",
            cwd=tmp_root,
        )
        _assert(rc == 0, f"run_pipeline.py asr (record-relative --input) exited with {rc}", errors)

    # Case C (regression for the manifest entry without 'path' key):
    # an artifact entry that uses 'storage_uri' instead of 'path' must not
    # raise KeyError; the pipeline should fall through to the filesystem
    # glob and still find voice_master.wav.
    with tempfile.TemporaryDirectory() as tmp:
        record_no_path = _make_synthetic_record(
            Path(tmp),
            manifest_artifacts=[
                {"kind": "audio", "storage_uri": "s3://example/voice.wav"}
            ],
        )
        rc = _run_pipeline(record_no_path)
        _assert(rc == 0, f"run_pipeline.py asr (manifest entry without 'path') exited with {rc}", errors)

    # Case D (regression for --output-dir outside the record tree):
    # this used to raise ValueError from .relative_to(); now the descriptor
    # falls back to a synthetic derived/asr/<name> path.
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        record_alt = _make_synthetic_record(Path(tmp_in))
        rc = _run_pipeline(record_alt, output_dir=Path(tmp_out))
        _assert(rc == 0, f"run_pipeline.py asr (--output-dir outside record) exited with {rc}", errors)
        out_descriptor = Path(tmp_out) / "voice_master.transcript.descriptor.json"
        if out_descriptor.exists():
            d = json.loads(out_descriptor.read_text(encoding="utf-8"))
            _assert(
                d.get("output", {}).get("path", "").startswith("derived/asr/"),
                "descriptor.output.path doesn't fall back to derived/asr/ when --output-dir is outside record",
                errors,
            )

    # Re-create the original record so the post-block assertions still find it.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        record = _make_synthetic_record(tmp_root)
        rc = _run_pipeline(record)
        _assert(rc == 0, f"run_pipeline.py asr (final case) exited with {rc}", errors)

        derived_dir = record / "derived" / "asr"
        transcript = derived_dir / "voice_master.transcript.json"
        descriptor = derived_dir / "voice_master.transcript.descriptor.json"

        _assert(transcript.exists(), f"missing transcript at {transcript}", errors)
        _assert(descriptor.exists(), f"missing descriptor at {descriptor}", errors)

        if transcript.exists():
            t = json.loads(transcript.read_text(encoding="utf-8"))
            _assert(t.get("backend") == "dummy", "transcript.backend != dummy", errors)
            _assert(t.get("language") == "zh", "transcript.language != zh (CLI override ignored)", errors)
            _assert(len(t.get("segments", [])) >= 1, "transcript has no segments", errors)
            _assert(
                t.get("audio_sha256", "").startswith("sha256:"),
                "transcript.audio_sha256 not a sha256 hash",
                errors,
            )

        if descriptor.exists():
            d = json.loads(descriptor.read_text(encoding="utf-8"))
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            schema_errors = sorted(Draft202012Validator(schema).iter_errors(d), key=lambda e: e.path)
            for se in schema_errors:
                errors.append(f"descriptor schema error at {'/'.join(map(str, se.path)) or '<root>'}: {se.message}")
            _assert(d.get("pipeline") == "asr", "descriptor.pipeline != asr", errors)
            _assert(
                d.get("output", {}).get("path", "").startswith("derived/asr/"),
                "descriptor.output.path doesn't start with derived/asr/",
                errors,
            )
            _assert(
                d.get("model", {}).get("online_api_used") is False,
                "descriptor.model.online_api_used is not False",
                errors,
            )

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"test_asr_pipeline: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("test_asr_pipeline: ASR pipeline + descriptor end-to-end OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
