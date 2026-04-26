#!/usr/bin/env python3
"""Static validation of every DLRS pipeline.

This validator does NOT execute the pipelines (so it is safe to run in CI
without GPUs, network access, or heavy optional dependencies). It enforces
the contract documented in :mod:`pipelines.PipelineSpec`:

1. Every module listed in ``pipelines.PIPELINE_MODULES`` exposes a ``SPEC``.
2. The ``SPEC`` declares ``inputs``, ``outputs`` and an
   ``output_pointer_template`` shaped ``derived/<name>/...``.
3. The pipeline does not advertise hosted-API dependencies via
   ``online_apis_used`` (offline-first invariant for v0.5).
4. The CLI dispatcher (``tools/run_pipeline.py``) can render ``--help`` for
   every pipeline without importing optional heavy dependencies.

Add it to ``tools/batch_validate.py`` as a step so CI exercises it.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines import PipelineSpec, load_specs  # noqa: E402


def _validate_spec(spec: PipelineSpec) -> list[str]:
    errors: list[str] = []
    if not spec.name or not re.fullmatch(r"[a-z][a-z0-9_]*", spec.name):
        errors.append(f"{spec.name!r}: name must be lower_snake_case")
    if not spec.description:
        errors.append(f"{spec.name}: description is empty")
    if not spec.inputs:
        errors.append(f"{spec.name}: inputs is empty")
    if not spec.outputs:
        errors.append(f"{spec.name}: outputs is empty")
    expected_prefix = f"derived/{spec.name}/"
    if not spec.output_pointer_template.startswith(expected_prefix):
        errors.append(
            f"{spec.name}: output_pointer_template must start with {expected_prefix!r}, "
            f"got {spec.output_pointer_template!r}"
        )
    if spec.online_apis_used:
        errors.append(
            f"{spec.name}: declares online_apis_used={spec.online_apis_used!r}; "
            "v0.5 pipelines must be offline-first"
        )
    return errors


def _validate_help(spec: PipelineSpec) -> list[str]:
    """Make sure ``run_pipeline.py <name> --help`` exits cleanly."""
    cmd = [sys.executable, str(ROOT / "tools" / "run_pipeline.py"), spec.name, "--help"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"{spec.name}: --help exited with {proc.returncode}: {proc.stderr.strip()}"]
    return []


def _validate_no_hosted_api_imports() -> list[str]:
    """Cheap grep guard: nothing under pipelines/ may import hosted-API SDKs."""
    # Single shared alternation for both ``from X ...`` and ``import X`` so we
    # cannot accidentally end up with the two branches enumerating different
    # packages. ``google\.generativeai`` and ``aliyun_sdk_bailian`` are dotted
    # / underscore module paths but the same alternation handles both because
    # ``\.`` in a ``from`` matches a literal dot and ``\b`` after the last
    # token still terminates correctly for ``import google.generativeai``.
    hosted_pkgs = (
        r"openai|anthropic|google\.generativeai|cohere|deepl|"
        r"replicate|aliyun_sdk_bailian"
    )
    forbidden = re.compile(
        rf"^\s*(?:from\s+(?:{hosted_pkgs})\b|import\s+(?:{hosted_pkgs})\b)",
        re.MULTILINE,
    )
    errors: list[str] = []
    for py in (ROOT / "pipelines").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if forbidden.search(text):
            errors.append(f"{py.relative_to(ROOT)}: imports a hosted-API SDK; v0.5 is offline-first")
    return errors


def main() -> int:
    specs = load_specs()
    errors: list[str] = []
    for spec in specs:
        errors.extend(_validate_spec(spec))
        errors.extend(_validate_help(spec))
    errors.extend(_validate_no_hosted_api_imports())

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"validate_pipelines: {len(errors)} error(s) across {len(specs)} pipeline(s)", file=sys.stderr)
        return 1

    print(f"validate_pipelines: {len(specs)} pipeline(s) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
