"""Stage 1.7 — Lifecycle gate.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` Part B §B.1 row 1 + v0.8
``docs/LIFE_LIFECYCLE_SPEC.md``.

The gate behaviour:

- ``active`` / ``superseded`` → proceed (Stage 2 carries on).
- ``frozen`` (memorial) → proceed but flag the runtime so Stage 4 Run
  enters memorial read-only mode (full enforcement of memorial mode is
  v0.9 sub-issue #125 — Stage 5 Guard).
- ``withdrawn`` → reject.
- ``tainted`` → reject (per lifecycle spec a tainted package MUST NOT
  be served).

Packages predating v0.8 do not carry ``lifecycle/lifecycle.json``;
absence is treated as ``active`` (the v0.7 default) and a warning is
recorded so the runtime operator knows the package is pre-v0.8.
"""

from __future__ import annotations

import json
import zipfile
from typing import Any

from runtime.verify.result import VerifyResult


_LIFECYCLE_PATH = "lifecycle/lifecycle.json"
_VALID_STATES = {"active", "superseded", "frozen", "withdrawn", "tainted"}


def gate_lifecycle(zf: zipfile.ZipFile, vr: VerifyResult) -> bool:
    if _LIFECYCLE_PATH not in zf.namelist():
        vr.lifecycle_state = "active"
        vr.warnings.append(
            f"{_LIFECYCLE_PATH} absent — treating package as `active` "
            "(pre-v0.8 emission)."
        )
        return True

    try:
        raw = zf.read(_LIFECYCLE_PATH)
    except KeyError:  # pragma: no cover — guarded above
        vr.add_error("lifecycle", "lifecycle_unreadable", _LIFECYCLE_PATH)
        return False
    try:
        doc: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        vr.add_error("lifecycle", "lifecycle_unparseable", str(exc))
        return False
    if not isinstance(doc, dict):
        vr.add_error("lifecycle", "lifecycle_not_object")
        return False

    state = doc.get("lifecycle_state")
    if not isinstance(state, str):
        vr.add_error("lifecycle", "lifecycle_state_missing")
        return False
    if state not in _VALID_STATES:
        vr.add_error("lifecycle", "lifecycle_state_unknown", state)
        return False

    vr.lifecycle_state = state

    if state == "withdrawn":
        vr.add_error("lifecycle", "package_withdrawn")
        return False
    if state == "tainted":
        vr.add_error("lifecycle", "package_tainted")
        return False
    if state == "frozen":
        vr.warnings.append(
            "package lifecycle_state=frozen — Stage 4 Run will enter "
            "memorial read-only mode (full enforcement at sub-issue #125)."
        )

    return True
