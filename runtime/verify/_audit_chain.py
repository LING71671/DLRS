"""Stage 1.5 — Audit chain verification.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.4 + v0.4 audit hash-chain
semantics (canonical JSON: sorted keys, no whitespace; hash = ``sha256:``
+ hex of the canonical-without-``hash`` line).

Steps:

1. Read ``audit/events.jsonl`` line by line.
2. For each event verify ``hash`` is the canonical sha256 of the rest
   of the event AND that ``prev_hash`` matches the previous event's
   ``hash`` (or is ``null`` for the first event).
3. Resolve ``life-package.json::audit_event_ref`` (``audit/events.jsonl#L<n>``)
   and verify the referenced line is a ``package_emitted`` event whose
   payload references the package's ``package_id``.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from typing import Any

from runtime.verify.result import VerifyResult


_AUDIT_PATH = "audit/events.jsonl"
_AUDIT_REF_RE = re.compile(r"^audit/events\.jsonl#L([1-9][0-9]*)$")


def _canonical_dump(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_of(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def verify_audit_chain(
    zf: zipfile.ZipFile,
    descriptor: dict[str, Any],
    vr: VerifyResult,
) -> bool:
    if _AUDIT_PATH not in zf.namelist():
        vr.add_error("audit_chain", "audit_log_missing", _AUDIT_PATH)
        return False

    try:
        raw = zf.read(_AUDIT_PATH).decode("utf-8")
    except UnicodeDecodeError as exc:
        vr.add_error("audit_chain", "audit_log_not_utf8", str(exc))
        return False
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        vr.add_error("audit_chain", "audit_log_empty")
        return False

    parsed: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        try:
            evt = json.loads(line)
        except json.JSONDecodeError as exc:
            vr.add_error(
                "audit_chain",
                "audit_line_not_json",
                f"L{idx}: {exc}",
            )
            return False
        if not isinstance(evt, dict):
            vr.add_error("audit_chain", "audit_line_not_object", f"L{idx}")
            return False
        parsed.append(evt)

    prev_hash: str | None = None
    for idx, evt in enumerate(parsed, start=1):
        declared_prev = evt.get("prev_hash", None)
        if declared_prev != prev_hash:
            vr.add_error(
                "audit_chain",
                "prev_hash_break",
                f"L{idx}: declared={declared_prev!r} expected={prev_hash!r}",
            )
            return False

        declared_hash = evt.get("hash")
        if not isinstance(declared_hash, str):
            vr.add_error(
                "audit_chain",
                "missing_hash",
                f"L{idx}",
            )
            return False
        recompute_input = {k: v for k, v in evt.items() if k != "hash"}
        recomputed = _sha256_of(_canonical_dump(recompute_input))
        if recomputed != declared_hash:
            vr.add_error(
                "audit_chain",
                "hash_mismatch",
                f"L{idx}: declared={declared_hash} recomputed={recomputed}",
            )
            return False
        prev_hash = declared_hash

    vr.audit_chain_length = len(parsed)

    aer = descriptor.get("audit_event_ref")
    if not isinstance(aer, str):
        vr.add_error("audit_chain", "audit_event_ref_missing")
        return False
    m = _AUDIT_REF_RE.match(aer)
    if not m:
        vr.add_error(
            "audit_chain",
            "audit_event_ref_unparseable",
            aer,
        )
        return False
    line_num = int(m.group(1))
    if line_num < 1 or line_num > len(parsed):
        vr.add_error(
            "audit_chain",
            "audit_event_ref_out_of_range",
            f"line={line_num} chain_length={len(parsed)}",
        )
        return False

    referenced = parsed[line_num - 1]
    if referenced.get("event_type") != "package_emitted":
        vr.add_error(
            "audit_chain",
            "audit_event_ref_wrong_type",
            f"event_type={referenced.get('event_type')!r}",
        )
        return False
    metadata = referenced.get("metadata") or {}
    declared_pkg = metadata.get("package_id") if isinstance(metadata, dict) else None
    if declared_pkg != descriptor.get("package_id"):
        vr.add_error(
            "audit_chain",
            "audit_event_ref_wrong_package",
            f"event.package_id={declared_pkg!r} descriptor.package_id={descriptor.get('package_id')!r}",
        )
        return False

    return True
