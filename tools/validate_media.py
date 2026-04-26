#!/usr/bin/env python3
"""Validate DLRS pointer media metadata.

Walks every ``*.pointer.json`` under ``humans/`` and ``examples/`` and checks
that the pointer:

1. Conforms to ``schemas/pointer.schema.json``.
2. Carries the minimum ``media_metadata`` required by
   ``docs/COLLECTION_STANDARD.md`` for its ``artifact_type``.

If a local sample file is present alongside the pointer (e.g. for tests),
``ffprobe`` is invoked when available to cross-check the declared metadata.
The validator never downloads remote object storage assets.

Exit code is non-zero on validation failures.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "pointer.schema.json"

# Minimum collection-standard thresholds. Mirrors docs/COLLECTION_STANDARD.md.
MINIMUMS: dict[str, dict[str, Any]] = {
    "audio": {
        "required_fields": ["duration_seconds", "sample_rate_hz", "bit_depth", "format"],
        "format": {"wav", "flac", "mp3", "ogg", "m4a", "aac"},
        "sample_rate_hz_min": 44100,
        "bit_depth_min": 16,
        "duration_seconds_min": 60,
    },
    "video": {
        "required_fields": ["duration_seconds", "width", "height", "fps", "container"],
        "container": {"mp4", "mov", "mkv", "webm"},
        "min_height": 720,
        "fps_min": 24,
        "duration_seconds_min": 30,
    },
    "image": {
        "required_fields": ["width", "height", "format"],
        "format": {"png", "jpg", "jpeg", "tif", "tiff", "webp"},
        "min_long_edge": 512,
    },
    "text": {
        "required_fields": ["language", "character_count"],
        "character_count_min": 10000,
    },
    "avatar_3d": {
        "required_fields": ["format"],
        "format": {"vrm", "glb", "gltf", "fbx", "obj", "usd", "usdz"},
    },
    "document": {
        "required_fields": [],
    },
    "embedding": {
        "required_fields": [],
    },
}


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _iter_pointer_files() -> Iterable[Path]:
    for base in ("humans", "examples"):
        root = ROOT / base
        if root.exists():
            yield from sorted(root.rglob("*.pointer.json"))


def _check_schema(pointer: dict, errors: list[str]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.append("jsonschema package not installed; run pip install -r tools/requirements.txt")
        return
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    for e in sorted(validator.iter_errors(pointer), key=lambda e: list(e.path)):
        loc = "/".join(map(str, e.path)) or "<root>"
        errors.append(f"schema: {loc}: {e.message}")


def _check_media_metadata(pointer: dict, errors: list[str]) -> None:
    artifact_type = pointer.get("artifact_type")
    if not artifact_type:
        # Older pointer files don't declare artifact_type; warn but don't fail.
        errors.append("warning: pointer is missing optional field 'artifact_type' (recommended in v0.3)")
        return
    rules = MINIMUMS.get(artifact_type)
    if rules is None:
        errors.append(f"unsupported artifact_type: {artifact_type}")
        return
    media = pointer.get("media_metadata") or {}
    for required in rules.get("required_fields", []):
        if required not in media:
            errors.append(f"media_metadata.{required} required for artifact_type={artifact_type}")
    if artifact_type == "audio":
        sr = media.get("sample_rate_hz")
        if isinstance(sr, int) and sr < rules["sample_rate_hz_min"]:
            errors.append(f"audio sample_rate_hz {sr} < minimum {rules['sample_rate_hz_min']}")
        bd = media.get("bit_depth")
        if isinstance(bd, int) and bd < rules["bit_depth_min"]:
            errors.append(f"audio bit_depth {bd} < minimum {rules['bit_depth_min']}")
        ds = media.get("duration_seconds")
        if isinstance(ds, (int, float)) and ds < rules["duration_seconds_min"]:
            errors.append(f"audio duration_seconds {ds} < minimum {rules['duration_seconds_min']}")
        fmt = (media.get("format") or pointer.get("format") or "").lower()
        if fmt and fmt not in rules["format"]:
            errors.append(f"audio format {fmt!r} not in allowed list {sorted(rules['format'])}")
    elif artifact_type == "video":
        h = media.get("height")
        if isinstance(h, int) and h < rules["min_height"]:
            errors.append(f"video height {h} < minimum {rules['min_height']}")
        fps = media.get("fps")
        if isinstance(fps, (int, float)) and fps < rules["fps_min"]:
            errors.append(f"video fps {fps} < minimum {rules['fps_min']}")
        ds = media.get("duration_seconds")
        if isinstance(ds, (int, float)) and ds < rules["duration_seconds_min"]:
            errors.append(f"video duration_seconds {ds} < minimum {rules['duration_seconds_min']}")
        cont = (media.get("container") or pointer.get("format") or "").lower()
        if cont and cont not in rules["container"]:
            errors.append(f"video container {cont!r} not in allowed list {sorted(rules['container'])}")
    elif artifact_type == "image":
        long_edge = max(media.get("width") or 0, media.get("height") or 0)
        if long_edge and long_edge < rules["min_long_edge"]:
            errors.append(f"image long_edge {long_edge} < minimum {rules['min_long_edge']}")
        fmt = (media.get("format") or pointer.get("format") or "").lower()
        if fmt and fmt not in rules["format"]:
            errors.append(f"image format {fmt!r} not in allowed list {sorted(rules['format'])}")
    elif artifact_type == "text":
        cc = media.get("character_count")
        if isinstance(cc, int) and cc < rules["character_count_min"]:
            errors.append(f"text character_count {cc} < minimum {rules['character_count_min']}")
    elif artifact_type == "avatar_3d":
        fmt = (media.get("format") or pointer.get("format") or "").lower()
        if fmt and fmt not in rules["format"]:
            errors.append(f"avatar_3d format {fmt!r} not in allowed list {sorted(rules['format'])}")


def _maybe_check_local_sample(pointer_path: Path, pointer: dict, errors: list[str]) -> None:
    """If a local sample sits next to the pointer, cross-check with ffprobe."""
    sibling = pointer.get("local_sample_ref")
    if not sibling:
        return
    sample_path = (pointer_path.parent / sibling).resolve()
    if not sample_path.exists():
        errors.append(f"local_sample_ref points to missing file: {sample_path}")
        return
    if not shutil.which("ffprobe"):
        errors.append(f"warning: ffprobe not available; skipping local cross-check for {sample_path.name}")
        return
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,sample_rate,channels,width,height,r_frame_rate,duration",
                "-of", "json", str(sample_path),
            ],
            text=True, capture_output=True, check=True, timeout=20,
        ).stdout
        probe = json.loads(out)
    except subprocess.SubprocessError as exc:
        errors.append(f"ffprobe failed for {sample_path}: {exc}")
        return
    streams = probe.get("streams") or []
    if not streams:
        errors.append(f"ffprobe found no streams in {sample_path}")
        return
    media = pointer.get("media_metadata") or {}
    for s in streams:
        if s.get("codec_type") == "audio":
            declared = media.get("sample_rate_hz")
            actual = int(s.get("sample_rate") or 0)
            if declared and actual and declared != actual:
                errors.append(f"declared sample_rate_hz={declared} != ffprobe {actual} for {sample_path.name}")
        elif s.get("codec_type") == "video":
            for axis in ("width", "height"):
                declared = media.get(axis)
                actual = s.get(axis)
                if declared and actual and declared != actual:
                    errors.append(f"declared {axis}={declared} != ffprobe {actual} for {sample_path.name}")


def validate_pointer(path: Path) -> list[str]:
    pointer = _load_json(path)
    errors: list[str] = []
    _check_schema(pointer, errors)
    _check_media_metadata(pointer, errors)
    _maybe_check_local_sample(path, pointer, errors)
    return errors


def main(argv: list[str]) -> int:
    targets: list[Path]
    if len(argv) > 1:
        targets = [Path(a).resolve() for a in argv[1:]]
    else:
        targets = list(_iter_pointer_files())

    if not targets:
        print("validate_media: no *.pointer.json files found")
        return 0

    fatal_count = 0
    warn_count = 0
    for path in targets:
        rel = path.relative_to(ROOT) if path.is_absolute() and ROOT in path.parents else path
        errors = validate_pointer(path)
        fatal = [e for e in errors if not e.startswith("warning:")]
        warns = [e for e in errors if e.startswith("warning:")]
        if fatal:
            print(f"FAIL {rel}")
            for e in fatal:
                print(f"  - {e}")
            fatal_count += 1
        else:
            print(f"OK   {rel}")
        for w in warns:
            print(f"  ! {w}")
            warn_count += 1

    print()
    print(f"validate_media: pointers={len(targets)} failed={fatal_count} warnings={warn_count}")
    return 1 if fatal_count else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
