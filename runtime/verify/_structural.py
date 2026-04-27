"""Stage 1.1 — Open + structural validation.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.1.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from runtime.verify.result import VerifyResult


_DESCRIPTOR_NAME = "life-package.json"


def _is_safe_member_name(name: str) -> bool:
    """Reject path traversal / absolute paths / device paths inside the zip.

    The .life format is a portable archive — every entry must be a plain
    relative POSIX path with no ``..`` segment and no leading ``/``.
    """

    if not name:
        return False
    if name.startswith("/") or "\\" in name:
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    return True


def open_archive(life_path: Path, vr: VerifyResult) -> zipfile.ZipFile | None:
    """Open the .life archive and validate its structural shape.

    On success returns the open ``ZipFile`` (caller is responsible for
    closing). On failure adds an error to ``vr`` and returns ``None``.
    """

    if not life_path.exists():
        vr.add_error("structural", "life_path_missing", str(life_path))
        return None
    if not life_path.is_file():
        vr.add_error("structural", "life_path_not_file", str(life_path))
        return None

    try:
        zf = zipfile.ZipFile(life_path, "r")
    except zipfile.BadZipFile as exc:
        vr.add_error("structural", "bad_zip", str(exc))
        return None
    except OSError as exc:
        vr.add_error("structural", "open_failed", str(exc))
        return None

    # Reject path-traversal / absolute / backslash names.
    bad_names = [
        info.filename
        for info in zf.infolist()
        if not info.is_dir() and not _is_safe_member_name(info.filename)
    ]
    if bad_names:
        vr.add_error(
            "structural",
            "unsafe_zip_member_name",
            ", ".join(sorted(bad_names)[:5]),
        )
        zf.close()
        return None

    if _DESCRIPTOR_NAME not in zf.namelist():
        vr.add_error("structural", "missing_life_package_json")
        zf.close()
        return None

    return zf


def parse_descriptor(zf: zipfile.ZipFile, vr: VerifyResult) -> dict[str, Any] | None:
    """Read + ``json.loads`` ``life-package.json``."""

    try:
        raw = zf.read(_DESCRIPTOR_NAME)
    except KeyError:
        vr.add_error("structural", "missing_life_package_json")
        return None

    try:
        descriptor: Any = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        vr.add_error("structural", "descriptor_not_utf8", str(exc))
        return None
    except json.JSONDecodeError as exc:
        vr.add_error("structural", "descriptor_not_json", str(exc))
        return None

    if not isinstance(descriptor, dict):
        vr.add_error(
            "structural",
            "descriptor_not_object",
            f"top-level type was {type(descriptor).__name__}",
        )
        return None

    vr.descriptor = descriptor
    vr.package_id = descriptor.get("package_id")
    vr.schema_version = descriptor.get("schema_version")
    vr.mode = descriptor.get("mode")
    vr.record_id = descriptor.get("record_id")
    vr.created_at = descriptor.get("created_at")
    vr.expires_at = descriptor.get("expires_at")
    rc = descriptor.get("runtime_compatibility")
    if isinstance(rc, list):
        vr.runtime_compatibility = [str(x) for x in rc]
    fu = descriptor.get("forbidden_uses")
    if isinstance(fu, list):
        vr.forbidden_uses = [str(x) for x in fu]
    aer = descriptor.get("audit_event_ref")
    if isinstance(aer, str):
        vr.audit_event_ref = aer
    return descriptor
