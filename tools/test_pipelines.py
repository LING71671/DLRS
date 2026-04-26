#!/usr/bin/env python3
"""Umbrella driver for the DLRS pipeline test suite.

Dispatches every per-pipeline test script *and* every cross-cutting v0.6
test (audit bridge, hosted-API policy gate, memory-graph demo) as a
subprocess so an import failure in one suite cannot mask test results
in another. Each subprocess gets the same Python interpreter, so
virtual-env isolation works as expected.

Exit codes:

- ``0`` — every test passed.
- ``1`` — at least one test failed (per-test output is preserved on
  stderr so CI logs still show which assertion blew up).

This is what ``.github/workflows/validate.yml`` calls (single matrix
step) and what ``tools/batch_validate.py`` invokes as the ``pipelines``
step.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

# Per-pipeline tests (v0.5 + v0.6).
PER_PIPELINE_TESTS: list[tuple[str, Path]] = [
    ("asr", TOOLS / "test_asr_pipeline.py"),
    ("text", TOOLS / "test_text_pipeline.py"),
    ("vectorization", TOOLS / "test_vectorization_pipeline.py"),
    ("moderation", TOOLS / "test_moderation_pipeline.py"),
    ("memory_atoms", TOOLS / "test_memory_atoms_pipeline.py"),
    ("knowledge_graph", TOOLS / "test_knowledge_graph_pipeline.py"),
]

# v0.6 cross-cutting tests that span multiple pipelines.
CROSS_CUTTING_TESTS: list[tuple[str, Path]] = [
    ("audit_bridge", TOOLS / "test_descriptor_audit_bridge.py"),
    ("hosted_api_policy", TOOLS / "test_hosted_api_policy.py"),
    ("memory_graph_demo", TOOLS / "test_memory_graph_demo.py"),
]

PIPELINE_TESTS: list[tuple[str, Path]] = PER_PIPELINE_TESTS + CROSS_CUTTING_TESTS


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
    print(
        f"test_pipelines: running {len(PER_PIPELINE_TESTS)} per-pipeline + "
        f"{len(CROSS_CUTTING_TESTS)} cross-cutting tests"
    )
    results: list[dict] = []
    for name, path in PIPELINE_TESTS:
        result = run_one(name, path)
        results.append(result)
        marker = "OK " if result["ok"] else "FAIL"
        print(f"  [{marker}] {name:<18} ({result['elapsed']}s)")

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"\ntest_pipelines: {passed}/{total} suites green")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
