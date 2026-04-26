#!/usr/bin/env python3
"""Umbrella driver for the v0.5 pipeline test suite.

Runs every per-pipeline test script as a subprocess so an import failure
(e.g. a stray top-level ``from faster_whisper import WhisperModel``) in
one pipeline cannot mask test results in another. Each subprocess gets
the same Python interpreter, so virtual-env isolation works as expected.

Exit codes:

- ``0`` — every pipeline test passed.
- ``1`` — at least one pipeline test failed (per-pipeline output is
  preserved on stderr so CI logs still show which assertion blew up).

This is what ``.github/workflows/validate.yml`` calls and what
``tools/batch_validate.py`` invokes as the ``pipelines`` step.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

PIPELINE_TESTS: list[tuple[str, Path]] = [
    ("asr", TOOLS / "test_asr_pipeline.py"),
    ("text", TOOLS / "test_text_pipeline.py"),
    ("vectorization", TOOLS / "test_vectorization_pipeline.py"),
    ("moderation", TOOLS / "test_moderation_pipeline.py"),
]


def run_one(name: str, path: Path) -> dict:
    if not path.exists():
        return {"name": name, "ok": False, "elapsed": 0.0, "reason": f"missing test file: {path}"}
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    elapsed = time.perf_counter() - start
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        sys.stderr.write(f"\n--- {name} stderr ---\n{err}\n")
    elif err:
        # Some tests print a single OK line on stderr; surface it for visibility.
        sys.stderr.write(f"--- {name} stderr ---\n{err}\n")
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "elapsed": round(elapsed, 3),
        "stdout": out,
    }


def main() -> int:
    print(f"test_pipelines: running {len(PIPELINE_TESTS)} pipelines")
    results: list[dict] = []
    for name, path in PIPELINE_TESTS:
        result = run_one(name, path)
        results.append(result)
        marker = "OK " if result["ok"] else "FAIL"
        print(f"  [{marker}] {name:<14} ({result['elapsed']}s)")

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"\ntest_pipelines: {passed}/{total} pipelines green")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
