#!/usr/bin/env python3
"""Upload a local sensitive asset to object storage and emit a DLRS pointer.

Supports four backends, selected by URI scheme on ``--target``:

  * ``s3://``    Amazon S3 / S3-compatible (uses boto3 if available)
  * ``oss://``   Alibaba Cloud OSS         (uses oss2 if available)
  * ``cos://``   Tencent Cloud COS         (uses qcloud_cos if available)
  * ``minio://`` MinIO                     (uses minio python SDK if available)

The script will compute a SHA-256 checksum, derive ``size_bytes``, optionally
probe media metadata via ``ffprobe`` if installed, perform the upload, and
write a ``*.pointer.json`` next to ``--out`` that conforms to
``schemas/pointer.schema.json``.

This is a v0.3 reference implementation: it intentionally avoids embedding
credentials and reads them from the standard env vars / cred files of each
SDK. If the SDK for the chosen backend is not installed, the script will
print actionable installation instructions and exit non-zero.

Usage:
  python tools/upload_to_storage.py \\
      --source /path/to/voice_master.wav \\
      --target s3://dlrs-private-vault/humans/.../voice_master.wav \\
      --region us-west-2 \\
      --sensitivity S3_BIOMETRIC \\
      --access-policy private_runtime_only \\
      --artifact-type audio \\
      --out humans/.../artifacts/raw_pointers/audio/voice_master.pointer.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SUPPORTED_SCHEMES = {"s3", "oss", "cos", "minio", "obj"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def parse_target(target: str) -> tuple[str, str, str]:
    """Return (scheme, bucket, key). e.g. s3://bucket/path/key -> ('s3', 'bucket', 'path/key')."""
    p = urlparse(target)
    if p.scheme not in SUPPORTED_SCHEMES:
        raise ValueError(f"Unsupported target scheme: {p.scheme}")
    bucket = p.netloc
    key = p.path.lstrip("/")
    if not bucket or not key:
        raise ValueError(f"Invalid target URI: {target}")
    return p.scheme, bucket, key


def probe_media(path: Path) -> dict[str, Any]:
    if not shutil.which("ffprobe"):
        return {}
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=codec_type,codec_name,sample_rate,channels,width,height,r_frame_rate,duration",
                "-show_entries", "format=duration",
                "-of", "json", str(path),
            ],
            text=True, capture_output=True, check=True, timeout=30,
        ).stdout
        probe = json.loads(out)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return {}
    media: dict[str, Any] = {}
    fmt_dur = probe.get("format", {}).get("duration")
    if fmt_dur:
        try:
            media["duration_seconds"] = float(fmt_dur)
        except ValueError:
            pass
    for s in probe.get("streams", []):
        if s.get("codec_type") == "audio" and "sample_rate_hz" not in media:
            try:
                media["sample_rate_hz"] = int(s.get("sample_rate"))
            except (TypeError, ValueError):
                pass
            if s.get("channels"):
                media["channels"] = int(s["channels"])
            if s.get("codec_name"):
                media["codec"] = s["codec_name"]
        elif s.get("codec_type") == "video" and "width" not in media:
            for k in ("width", "height"):
                if s.get(k):
                    media[k] = int(s[k])
            r = s.get("r_frame_rate")
            if r and "/" in r:
                num, den = r.split("/")
                try:
                    if int(den) != 0:
                        media["fps"] = round(int(num) / int(den), 3)
                except ValueError:
                    pass
            if s.get("codec_name"):
                media["codec"] = s["codec_name"]
    return media


def upload_s3(target: str, source: Path) -> None:
    try:
        import boto3  # type: ignore
    except ImportError:
        raise RuntimeError("boto3 is required for s3:// uploads. Install: pip install boto3")
    _, bucket, key = parse_target(target)
    client = boto3.client("s3")
    client.upload_file(str(source), bucket, key)


def upload_oss(target: str, source: Path) -> None:
    try:
        import oss2  # type: ignore
    except ImportError:
        raise RuntimeError("oss2 is required for oss:// uploads. Install: pip install oss2")
    import os
    _, bucket, key = parse_target(target)
    auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"], os.environ["OSS_ACCESS_KEY_SECRET"])
    endpoint = os.environ.get("OSS_ENDPOINT", "https://oss-cn-shanghai.aliyuncs.com")
    oss2.Bucket(auth, endpoint, bucket).put_object_from_file(key, str(source))


def upload_cos(target: str, source: Path) -> None:
    try:
        from qcloud_cos import CosConfig, CosS3Client  # type: ignore
    except ImportError:
        raise RuntimeError("qcloud_cos is required for cos:// uploads. Install: pip install cos-python-sdk-v5")
    import os
    _, bucket, key = parse_target(target)
    config = CosConfig(
        Region=os.environ.get("COS_REGION", "ap-shanghai"),
        SecretId=os.environ["COS_SECRET_ID"],
        SecretKey=os.environ["COS_SECRET_KEY"],
    )
    CosS3Client(config).upload_file(Bucket=bucket, Key=key, LocalFilePath=str(source))


def upload_minio(target: str, source: Path) -> None:
    try:
        from minio import Minio  # type: ignore
    except ImportError:
        raise RuntimeError("minio is required for minio:// uploads. Install: pip install minio")
    import os
    _, bucket, key = parse_target(target)
    endpoint = os.environ["MINIO_ENDPOINT"]
    client = Minio(
        endpoint,
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=os.environ.get("MINIO_SECURE", "true").lower() == "true",
    )
    client.fput_object(bucket, key, str(source))


def upload_obj(target: str, source: Path) -> None:
    """obj:// is a generic placeholder used in examples; no real upload is performed."""
    print(f"obj:// scheme is generic and does not perform an upload. Pointer will reference {target}.")


UPLOADERS = {
    "s3": upload_s3,
    "oss": upload_oss,
    "cos": upload_cos,
    "minio": upload_minio,
    "obj": upload_obj,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Upload a local asset and emit a DLRS pointer file.")
    p.add_argument("--source", required=True, help="Local path to the asset.")
    p.add_argument("--target", required=True, help="Destination URI, e.g. s3://bucket/path/key.")
    p.add_argument("--region", required=True, help="Storage region, e.g. us-west-2.")
    p.add_argument("--sensitivity", required=True,
                   choices=["S0_PUBLIC", "S1_INTERNAL", "S2_SENSITIVE", "S2_CONFIDENTIAL",
                            "S3_BIOMETRIC", "S4_RESTRICTED", "S4_IDENTITY"])
    p.add_argument("--access-policy", required=True,
                   choices=["private_runtime_only", "team_internal", "audit_only", "public_preview"])
    p.add_argument("--artifact-type", choices=list(("audio","video","image","text","avatar_3d","document","embedding")))
    p.add_argument("--retention-days", type=int, default=None)
    p.add_argument("--withdrawal-endpoint", default=None)
    p.add_argument("--consent-ref", default=None)
    p.add_argument("--out", required=True, help="Path to write the resulting *.pointer.json.")
    p.add_argument("--dry-run", action="store_true", help="Do not perform the upload; only emit the pointer.")
    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    source = Path(args.source).resolve()
    if not source.exists():
        print(f"ERROR: source not found: {source}")
        return 2

    scheme, _, _ = parse_target(args.target)

    if not args.dry_run:
        try:
            UPLOADERS[scheme](args.target, source)
        except Exception as exc:
            print(f"ERROR: upload failed: {exc}")
            return 1

    pointer: dict[str, Any] = {
        "storage_uri": args.target,
        "checksum": sha256_of(source),
        "region": args.region,
        "format": source.suffix.lstrip(".").lower() or "bin",
        "size_bytes": source.stat().st_size,
        "sensitivity": args.sensitivity,
        "access_policy": args.access_policy,
    }
    if args.artifact_type:
        pointer["artifact_type"] = args.artifact_type
        media = probe_media(source)
        if media:
            pointer["media_metadata"] = media
    if args.retention_days is not None:
        pointer["retention_days"] = args.retention_days
    if args.withdrawal_endpoint:
        pointer["withdrawal_endpoint"] = args.withdrawal_endpoint
    if args.consent_ref:
        pointer["consent_ref"] = args.consent_ref

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote pointer: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
