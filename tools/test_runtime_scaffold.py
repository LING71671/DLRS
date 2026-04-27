#!/usr/bin/env python3
"""Sanity tests for the v0.9 runtime scaffold (sub-issue #120).

Verifies:

1. `lifectl version` exits 0 and prints the expected version string.
2. `lifectl info <pkg>` exits non-zero with a "not yet implemented" stderr
   message.
3. `lifectl run <pkg>` exits non-zero with a "not yet implemented" stderr
   message.
4. `import runtime; from runtime import Runtime, __version__` works.
5. `pyproject.toml` parses + declares the `lifectl` console script.

Stages 1-5 (#121-#126) replace the "not yet implemented" stubs with the
full assembly pipeline.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _python() -> str:
    return sys.executable


def test_runtime_module_importable() -> None:
    proc = subprocess.run(
        [_python(), "-c", "import runtime; print(runtime.__version__)"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "0.9.0.dev0"


def test_runtime_class_present() -> None:
    proc = subprocess.run(
        [
            _python(),
            "-c",
            "from runtime import Runtime; r = Runtime(); print(r.protocol)",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "0.1.1"


def test_lifectl_version_via_module() -> None:
    proc = subprocess.run(
        [_python(), "-m", "runtime.cli.lifectl", "version"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert out.startswith("lifectl 0.9.0.dev0"), out
    assert "life-runtime v0.1.1" in out, out


def test_lifectl_info_rejects_missing_path() -> None:
    # Post-#121: `lifectl info` is wired to Stage 1 Verify. A missing
    # path still exits non-zero (life_path validation runs first).
    proc = subprocess.run(
        [_python(), "-m", "runtime.cli.lifectl", "info", "pretend.life"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "life_path" in proc.stderr or "does not exist" in proc.stderr


def test_lifectl_run_rejects_missing_path() -> None:
    # Post-#121: `lifectl run` runs Stage 1; a missing path produces a
    # structural failure that exits non-zero.
    proc = subprocess.run(
        [_python(), "-m", "runtime.cli.lifectl", "run", "pretend.life"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert (
        "Stage 1 Verify FAIL" in proc.stderr
        or "life_path" in proc.stderr
    )


def test_lifectl_help_lists_three_commands() -> None:
    proc = subprocess.run(
        [_python(), "-m", "runtime.cli.lifectl", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "version" in out
    assert "info" in out
    assert "run" in out


def test_pyproject_parses_and_declares_lifectl_script() -> None:
    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.is_file(), "pyproject.toml missing at repo root"

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover - py310 fallback
        import tomli as tomllib  # type: ignore[no-redef]

    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["name"] == "dlrs-runtime"
    assert data["project"]["version"] == "0.9.0.dev0"
    scripts = data["project"]["scripts"]
    assert scripts.get("lifectl") == "runtime.cli.lifectl:main", (
        "expected lifectl script entry pointing at runtime.cli.lifectl:main"
    )


def test_runtime_subpackages_present() -> None:
    runtime_dir = REPO_ROOT / "runtime"
    expected = {
        "cli",
        "verify",
        "resolve",
        "assemble",
        "run",
        "guard",
        "providers",
        "audit",
    }
    actual = {
        p.name
        for p in runtime_dir.iterdir()
        if p.is_dir() and not p.name.startswith("__")
    }
    assert expected.issubset(actual), (
        f"runtime/ missing sub-packages: {expected - actual}"
    )


def main() -> int:
    tests = [
        test_runtime_module_importable,
        test_runtime_class_present,
        test_lifectl_version_via_module,
        test_lifectl_info_rejects_missing_path,
        test_lifectl_run_rejects_missing_path,
        test_lifectl_help_lists_three_commands,
        test_pyproject_parses_and_declares_lifectl_script,
        test_runtime_subpackages_present,
    ]
    failures: list[str] = []
    for test in tests:
        name = test.__name__
        try:
            test()
        except AssertionError as exc:
            failures.append(f"FAIL  {name}: {exc}")
        except Exception as exc:  # pragma: no cover - surfacing unexpected errors
            failures.append(f"ERROR {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {name}")

    if failures:
        for line in failures:
            print(line, file=sys.stderr)
        print(f"\n{len(failures)} of {len(tests)} runtime-scaffold tests failed.", file=sys.stderr)
        return 1
    print(f"\n{len(tests)} runtime-scaffold tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
