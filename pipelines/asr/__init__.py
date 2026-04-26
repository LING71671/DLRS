"""ASR (automatic speech recognition) pipeline.

Default backend is `faster-whisper <https://github.com/SYSTRAN/faster-whisper>`_,
imported lazily so ``--help`` works without it. A ``dummy`` backend exists
for tests and offline examples; see :mod:`pipelines.asr.transcribe`.

Outputs (next to each input audio file):

- ``<record>/derived/asr/<stem>.transcript.json``
  Canonical transcript with segments, language, duration, and the input
  audio's sha256.
- ``<record>/derived/asr/<stem>.transcript.descriptor.json``
  Provenance / lineage descriptor that conforms to
  ``schemas/derived-asset.schema.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from pipelines import PipelineSpec
from pipelines._descriptor import (
    DescriptorBuilder,
    ModelInfo,
    validate_descriptor,
    write_json,
)

PIPELINE_VERSION = "0.5.0"

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def _register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--record",
        required=False,
        help="Path to the record directory (the folder that holds manifest.json). "
             "When set, --input may be omitted and the first audio pointer in the "
             "manifest is used.",
    )
    parser.add_argument(
        "--input",
        required=False,
        help="Path to a specific input audio file. May be combined with --record "
             "to resolve the input within a record's tree.",
    )
    parser.add_argument(
        "--model",
        default="small",
        help="faster-whisper model id (tiny, base, small, medium, large-v3). Default: small.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="ISO-639-1 language hint (e.g. 'zh', 'en'). Auto-detect when omitted.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Compute device. Default: cpu (offline-first).",
    )
    parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "dummy"],
        help="ASR backend. 'dummy' is for tests and offline demos; it does not run "
             "any ML model.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/asr/. When --record "
             "is omitted, the output sits next to --input under ./derived/asr/.",
    )


def _resolve_record_and_input(args: argparse.Namespace) -> tuple[Optional[Path], Path, str]:
    """Return (record_root, audio_path, pointer_relpath).

    ``pointer_relpath`` is the path that ends up in the descriptor's
    ``inputs.source_pointers``. It is relative to the record root when
    ``--record`` is set, and falls back to the file's basename otherwise.
    """
    record_root: Optional[Path] = Path(args.record).resolve() if args.record else None

    if args.input:
        audio_arg = Path(args.input)
        if record_root is not None and not audio_arg.is_absolute():
            audio = (record_root / args.input).resolve()
        else:
            audio = audio_arg.resolve()
    else:
        if record_root is None:
            raise SystemExit("[asr] one of --input or --record is required")
        audio = _first_audio_in_record(record_root)

    if not audio.exists():
        raise SystemExit(f"[asr] audio file not found: {audio}")

    if record_root is not None:
        try:
            pointer_rel = str(audio.relative_to(record_root))
        except ValueError:
            pointer_rel = audio.name
    else:
        pointer_rel = audio.name

    return record_root, audio, pointer_rel


def _first_audio_in_record(record_root: Path) -> Path:
    """Find the first audio pointer / raw audio file under a record."""
    manifest = record_root / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("artifacts", []):
                if item.get("kind") != "audio":
                    continue
                rel = item.get("path")
                if not rel:
                    # Newer schema versions use ``storage_uri`` for pointer-style
                    # artefacts; fall through to the filesystem glob below.
                    continue
                candidate = record_root / rel
                if candidate.exists():
                    return candidate
        except (OSError, json.JSONDecodeError):
            pass

    candidates: List[Path] = []
    for p in (record_root / "artifacts").rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            candidates.append(p)
    if not candidates:
        raise SystemExit(f"[asr] no audio file found under {record_root}")
    candidates.sort()
    return candidates[0]


def _read_record_id(record_root: Optional[Path], default: str) -> str:
    if record_root is None:
        return default
    manifest = record_root / "manifest.json"
    if not manifest.exists():
        return default
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("record_id", default)
    except (OSError, json.JSONDecodeError):
        return default


def _run(args: argparse.Namespace) -> int:
    from pipelines.asr.transcribe import transcribe

    record_root, audio, pointer_rel = _resolve_record_and_input(args)

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "asr"
    else:
        out_dir = audio.parent / "derived" / "asr"

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = audio.stem
    transcript_path = out_dir / f"{stem}.transcript.json"
    descriptor_path = out_dir / f"{stem}.transcript.descriptor.json"

    print(f"[asr] backend={args.backend} model={args.model} device={args.device}", file=sys.stderr)
    print(f"[asr] input={audio}", file=sys.stderr)

    result = transcribe(
        audio_path=audio,
        model=args.model,
        language=args.language,
        device=args.device,
        backend=args.backend,
    )

    write_json(transcript_path, result.to_dict())

    record_id = _read_record_id(record_root, default="dlrs_unknown")
    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="asr",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "model": args.model,
            "language": args.language,
            "device": args.device,
            "backend": args.backend,
        },
        model=ModelInfo(
            id=result.model_id,
            version=None,
            source="local-cache" if args.backend == "faster-whisper" else "dummy",
            online_api_used=False,
        ),
    )
    builder.add_input(source_pointer=pointer_rel, file_path=audio)

    if record_root is not None:
        try:
            out_path_in_record = str(transcript_path.relative_to(record_root))
        except ValueError:
            # --output-dir was set to a path outside the record tree. The
            # descriptor still needs a derived/<pipeline>/ path to satisfy
            # the schema, so fall back to a synthetic record-relative form.
            out_path_in_record = f"derived/asr/{transcript_path.name}"
    else:
        out_path_in_record = f"derived/asr/{transcript_path.name}"
    descriptor = builder.finalise(out_path_in_record, transcript_path)

    validate_descriptor(descriptor, SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    print(f"[asr] wrote {transcript_path}", file=sys.stderr)
    print(f"[asr] wrote {descriptor_path}", file=sys.stderr)
    print(
        f"[asr] segments={len(result.segments)} language={result.language} "
        f"duration={result.duration_seconds:.1f}s",
        file=sys.stderr,
    )
    return 0


SPEC = PipelineSpec(
    name="asr",
    description="Speech-to-text transcription with timestamps (default: faster-whisper, offline).",
    inputs=["audio/wav", "audio/mp3", "audio/m4a", "audio/flac"],
    outputs=["transcript.json", "transcript.descriptor.json"],
    dependencies=["faster-whisper>=1.0", "jsonschema>=4.20"],
    output_pointer_template="derived/asr/{stem}.transcript.json",
    register=_register,
    run=_run,
)
