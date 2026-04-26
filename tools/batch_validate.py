#!/usr/bin/env python3
"""Run every DLRS validator and emit a single machine-readable report.

This tool is intentionally a thin orchestrator over the existing per-tool
scripts so that the canonical pass/fail logic is not duplicated. The report
is a JSON document that captures, for each child tool: command, exit code,
stdout, stderr, duration, and a coarse pass/fail flag.

The CI pipeline (.github/workflows/validate.yml) uploads the report as an
artifact so downstream consumers (a future Web review console, dashboard,
or PR comment bot) can render results without having to re-parse logs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

DEFAULT_STEPS = [
    ("check_sensitive_files", [sys.executable, str(TOOLS / "check_sensitive_files.py")]),
    ("lint_schemas", [sys.executable, str(TOOLS / "lint_schemas.py")]),
    ("validate_repo", [sys.executable, str(TOOLS / "validate_repo.py")]),
    ("validate_examples", [sys.executable, str(TOOLS / "validate_examples.py")]),
    ("validate_media", [sys.executable, str(TOOLS / "validate_media.py")]),
    ("test_registry", [sys.executable, str(TOOLS / "test_registry.py")]),
    ("build_registry", [sys.executable, str(TOOLS / "build_registry.py")]),
    ("validate_pipelines", [sys.executable, str(TOOLS / "validate_pipelines.py")]),
    ("test_derived_asset_schema", [sys.executable, str(TOOLS / "test_derived_asset_schema.py")]),
    ("pipelines", [sys.executable, str(TOOLS / "test_pipelines.py")]),
    ("asr_demo", [sys.executable, str(TOOLS / "test_asr_demo.py")]),
]


def run_step(name: str, cmd: list[str]) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    duration = round(time.perf_counter() - start, 3)
    return {
        "step": name,
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "duration_seconds": duration,
        "stdout": proc.stdout.strip().splitlines(),
        "stderr": proc.stderr.strip().splitlines(),
        "passed": proc.returncode == 0,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report-dir", default=str(ROOT / "reports"), help="Where to write report JSON")
    p.add_argument("--fail-fast", action="store_true", help="Stop at the first failing step")
    p.add_argument("--include-build-registry", action="store_true",
                   help="DEPRECATED, build_registry already runs by default")
    args = p.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = report_dir / f"validate_{started}.json"

    results = []
    overall_pass = True
    for name, cmd in DEFAULT_STEPS:
        result = run_step(name, cmd)
        print(f"[{'OK' if result['passed'] else 'FAIL'}] {name}  ({result['duration_seconds']}s)")
        results.append(result)
        if not result["passed"]:
            overall_pass = False
            if args.fail_fast:
                break

    report = {
        "schema": "dlrs-batch-validate/1.0",
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_sha": os.environ.get("GITHUB_SHA") or _git_sha() or None,
        "branch": os.environ.get("GITHUB_REF_NAME") or _git_branch() or None,
        "passed": overall_pass,
        "step_count": len(results),
        "step_failures": sum(1 for r in results if not r["passed"]),
        "results": results,
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        display_path = out_path.resolve().relative_to(ROOT)
    except ValueError:
        display_path = out_path
    print(f"\nreport: {display_path}")
    print(f"summary: {report['step_count']-report['step_failures']}/{report['step_count']} passed")

    return 0 if overall_pass else 1


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def _git_branch() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
