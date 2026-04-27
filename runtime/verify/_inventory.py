"""Stage 1.4 — Inventory integrity.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.3.

Walk every entry in ``life-package.json::contents[]``:

- verify the path exists in the zip
- verify the decompressed sha256 matches
- verify the decompressed size matches

Then ensure every zip entry (other than ``life-package.json``) is listed
in ``contents[]`` — extra entries indicate tampering or build-tool
misuse and MUST be rejected.
"""

from __future__ import annotations

import hashlib
import zipfile
from typing import Any

from runtime.verify.result import VerifyResult


_DESCRIPTOR_NAME = "life-package.json"


def _strip_sha_prefix(s: str) -> str:
    return s[len("sha256:") :] if s.startswith("sha256:") else s


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def verify_inventory(
    zf: zipfile.ZipFile,
    descriptor: dict[str, Any],
    vr: VerifyResult,
) -> bool:
    contents = descriptor.get("contents", [])
    if not isinstance(contents, list):
        vr.add_error("inventory", "contents_not_array")
        return False

    listed_paths: set[str] = set()
    verified = 0

    for idx, entry in enumerate(contents):
        if not isinstance(entry, dict):
            vr.add_error("inventory", "entry_not_object", f"contents[{idx}]")
            return False
        path = entry.get("path")
        expected_sha = entry.get("sha256")
        expected_size = entry.get("size")
        if not isinstance(path, str):
            vr.add_error("inventory", "entry_path_missing", f"contents[{idx}]")
            return False
        if not isinstance(expected_sha, str):
            vr.add_error("inventory", "entry_sha_missing", path)
            return False
        if not isinstance(expected_size, int):
            vr.add_error("inventory", "entry_size_missing", path)
            return False

        listed_paths.add(path)

        try:
            data = zf.read(path)
        except KeyError:
            vr.add_error("inventory", "missing_zip_entry", path)
            return False

        if len(data) != expected_size:
            vr.add_error(
                "inventory",
                "size_mismatch",
                f"{path}: declared={expected_size} actual={len(data)}",
            )
            return False

        actual_sha = _sha256_bytes(data)
        if _strip_sha_prefix(actual_sha) != _strip_sha_prefix(expected_sha):
            vr.add_error(
                "inventory",
                "hash_mismatch",
                f"{path}: declared={expected_sha} actual={actual_sha}",
            )
            return False

        verified += 1

    actual_files = {
        info.filename
        for info in zf.infolist()
        if not info.is_dir()
    }
    extra = sorted(actual_files - listed_paths - {_DESCRIPTOR_NAME})
    if extra:
        vr.add_error(
            "inventory",
            "unlisted_zip_entry",
            ", ".join(extra[:5]) + (" …" if len(extra) > 5 else ""),
        )
        return False

    vr.inventory_entries_verified = verified
    return True
