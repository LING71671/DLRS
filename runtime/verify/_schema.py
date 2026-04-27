"""Stage 1.2 — Schema validation.

Spec: ``docs/LIFE_RUNTIME_STANDARD.md`` §2.1 (life-package schema) +
v0.8 ``docs/LIFE_BINDING_SPEC.md`` §7 (forbidden_uses key namespace).

The runtime trusts the existing repository schema at
``schemas/life-package.schema.json`` as its source of truth. Authoring-
time validation already runs against it via ``tools/build_life_package``
+ ``tools/test_life_package_schema``; the runtime re-validates at mount
because runtimes MUST NOT trust unverified inputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from runtime.verify.result import VerifyResult


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LIFE_PACKAGE_SCHEMA_PATH = _REPO_ROOT / "schemas" / "life-package.schema.json"


# v0.8 binding-spec §7 hybrid namespace — the core enum the runtime
# recognises out of the box. ``x-`` extension keys are advisory at v0.9
# (the runtime warns but does not reject); unknown non-``x-`` keys
# fail-close per binding-spec §7.
#
# The set is deliberately conservative for v0.9; the official registry
# document lives in the binding spec itself.  Any v0.7/v0.8-era life-
# package emitted by the existing builder uses the keys below.
_CORE_FORBIDDEN_USES_KEYS: set[str] = {
    # Identity / impersonation
    "impersonation_for_fraud",
    "impersonation_real_person",
    "voice_clone_for_fraud",
    "avatar_clone",
    # Memorial
    "memorial_reanimation_without_executor",
    # Sensitive content
    "explicit_content",
    "explicit_sexual_content",
    "harassment",
    "spam_advertising",
    # Influence / endorsement
    "political_endorsement",
    "fraud",
    # Specialised advice
    "medical_diagnosis",
    "legal_advice",
    "financial_advice",
}


def _load_schema() -> dict[str, Any]:
    return json.loads(_LIFE_PACKAGE_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_descriptor(descriptor: dict[str, Any], vr: VerifyResult) -> bool:
    """Validate ``life-package.json`` against its JSON Schema."""

    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(descriptor), key=lambda e: e.path)
    if errors:
        for err in errors:
            path = "/".join(str(p) for p in err.absolute_path) or "<root>"
            vr.add_error(
                "schema",
                "life_package_schema_violation",
                f"{path}: {err.message}",
            )
        return False
    return True


def validate_forbidden_uses_namespace(vr: VerifyResult) -> bool:
    """Reject unknown non-``x-`` ``forbidden_uses[]`` keys (binding-spec §7).

    ``x-`` extension keys are accepted but flagged via ``vr.warnings`` —
    the runtime recognises them as advisory until a Provider explicitly
    enforces them in Stage 4 Run.
    """

    ok = True
    for key in vr.forbidden_uses:
        if key.startswith("x-"):
            vr.warnings.append(
                f"forbidden_uses extension key {key!r} has no built-in enforcer "
                "(advisory only at v0.9; binding-spec §7)."
            )
            continue
        if key not in _CORE_FORBIDDEN_USES_KEYS:
            vr.add_error(
                "schema",
                "forbidden_use_unknown_key",
                f"{key!r} is not in the v0.8 core enum and lacks an `x-` prefix",
            )
            ok = False
    return ok
