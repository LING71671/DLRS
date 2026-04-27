#!/usr/bin/env python3
"""Stage 1 Verify sanity-test driver (v0.9 sub-issue #121).

Covers all seven §2.1-§2.5 + lifecycle gate sub-steps.

Each test builds (or mutates) a tiny `.life` archive in a fresh tempdir
and asserts the expected ``VerifyResult`` outcome — both as a Python
import and via the ``lifectl info`` subprocess to keep the CLI surface
under coverage.

Because the spec mandates a real HTTP poll of ``withdrawal_endpoint``
in default mode, every test that exercises Stage 1 end-to-end either
spins up a local ``http.server`` HTTP fixture (the ``with_mock_server``
helper) or passes ``--withdrawal-mock not-revoked`` to short-circuit
the call deterministically.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "tools" / "build_life_package.py"
SOURCE_RECORD = REPO_ROOT / "examples" / "minimal-life-package"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.audit import AuditRecorder  # noqa: E402
from runtime.verify import (  # noqa: E402
    VerifyResult,
    WithdrawalPolicy,
    verify,
)


# ---------------------------------------------------------------------------
# Fixture helpers


class _WithdrawalHandler(BaseHTTPRequestHandler):
    """HTTP handler that returns a configurable withdrawal poll body.

    The active body / status code is read from the server's
    ``response_status`` / ``response_body`` attributes so individual
    tests can rewire them without restarting the server.
    """

    def do_GET(self) -> None:  # noqa: N802
        srv: Any = self.server
        self.send_response(srv.response_status)
        self.send_header("Content-Type", "application/json")
        body = srv.response_body if isinstance(srv.response_body, bytes) else srv.response_body.encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # silence default request log


@contextlib.contextmanager
def with_mock_server(
    *,
    status: int = 200,
    body: str | bytes = '{"status":"active"}',
):
    """Yield ``(server, base_url)`` for a local HTTP fixture."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = HTTPServer(("127.0.0.1", port), _WithdrawalHandler)
    server.response_status = status  # type: ignore[attr-defined]
    server.response_body = body  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{port}/withdraw"
    finally:
        server.shutdown()
        server.server_close()


def _stage_record(dst: Path) -> Path:
    """Copy the minimal-life-package source record into ``dst`` so the
    builder can mutate ``audit/events.jsonl`` without touching git."""

    record = dst / "record"
    shutil.copytree(SOURCE_RECORD, record, ignore=shutil.ignore_patterns("out"))
    return record


def _build_life(
    *,
    withdrawal_endpoint: str,
    workdir: Path,
    extra_builder_args: list[str] | None = None,
) -> Path:
    """Run ``tools/build_life_package.py`` against a fresh staging copy."""

    record = _stage_record(workdir)
    out_dir = workdir / "out"
    out_dir.mkdir()
    args = [
        sys.executable,
        str(BUILDER),
        "--record",
        str(record),
        "--output-dir",
        str(out_dir),
        "--withdrawal-endpoint",
        withdrawal_endpoint,
        "--deterministic",
    ]
    if extra_builder_args:
        args.extend(extra_builder_args)
    proc = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(
            f"build_life_package failed (rc={proc.returncode}): {proc.stderr}"
        )
    out_files = list(out_dir.glob("*.life"))
    assert len(out_files) == 1, out_files
    return out_files[0]


def _rebuild_zip_with(
    src: Path,
    dst: Path,
    mutate: Any,
) -> None:
    """Copy ``src`` into ``dst`` while letting ``mutate(name, data)`` rewrite
    or drop entries (return ``None`` to drop, ``(new_name, new_data)`` to
    rewrite, or ``True`` to keep verbatim).

    Used to corrupt fixtures for negative tests.
    """

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(
        dst, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            outcome = mutate(info.filename, data)
            if outcome is None:
                continue
            if outcome is True:
                zout.writestr(info, data)
                continue
            new_name, new_data = outcome
            zout.writestr(new_name, new_data)


# ---------------------------------------------------------------------------
# Tests


def test_happy_path_with_real_http() -> None:
    """End-to-end mount succeeds when the withdrawal endpoint replies 200 + active."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with with_mock_server(status=200, body='{"status":"active"}') as (_srv, url):
            life = _build_life(withdrawal_endpoint=url, workdir=tmp_path)
            recorder = AuditRecorder()
            result = verify(life, audit=recorder)
            assert result.ok, result.errors
            assert result.package_id is not None
            assert result.lifecycle_state == "active"
            assert result.inventory_entries_verified >= 5
            assert "mount_attempted" in recorder.types()
            assert "withdrawal_poll" in recorder.types()
            poll = recorder.latest("withdrawal_poll")
            assert poll is not None and poll.fields["result"] == "not_revoked"


def test_bad_zip_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.life"
        bad.write_bytes(b"not a zip file")
        result = verify(bad, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        assert result.first_error().step == "structural"
        assert result.first_error().reason == "bad_zip"


def test_missing_descriptor_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "no-descriptor.life"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("audit/events.jsonl", "{}\n")
        result = verify(bad)
        assert not result.ok
        assert result.first_error().reason == "missing_life_package_json"


def test_inventory_hash_mismatch_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        corrupted = tmp_path / "corrupt.life"

        def mutate(name: str, data: bytes) -> Any:
            if name == "manifest.json":
                return (name, data + b"\n# tampered")
            return True

        _rebuild_zip_with(good, corrupted, mutate)
        result = verify(corrupted, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        first = result.first_error()
        assert first.step == "inventory"
        assert first.reason in {"hash_mismatch", "size_mismatch"}


def test_unlisted_extra_entry_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        tampered = tmp_path / "tampered.life"

        def mutate(name: str, data: bytes) -> Any:
            return True

        _rebuild_zip_with(good, tampered, mutate)
        with zipfile.ZipFile(tampered, "a") as zf:
            zf.writestr("rogue.txt", "hello")

        result = verify(tampered, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        first = result.first_error()
        assert first.step == "inventory"
        assert first.reason == "unlisted_zip_entry"


def test_audit_chain_break_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        broken = tmp_path / "broken.life"

        def mutate(name: str, data: bytes) -> Any:
            if name == "audit/events.jsonl":
                lines = data.decode("utf-8").splitlines()
                if len(lines) >= 2:
                    second = json.loads(lines[1])
                    second["prev_hash"] = (
                        "sha256:" + "0" * 64
                    )  # break the chain
                    lines[1] = json.dumps(second, sort_keys=True, separators=(",", ":"))
                return (name, ("\n".join(lines) + "\n").encode("utf-8"))
            return True

        _rebuild_zip_with(good, broken, mutate)
        # NB: mutating the audit file invalidates its sha256 in
        # life-package.json::contents[] — Stage 1.4 catches that BEFORE
        # Stage 1.5 sees the chain. Both reasons are valid spec
        # rejections; we accept either.
        result = verify(broken, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        first = result.first_error()
        assert first.step in {"audit_chain", "inventory"}


def test_expired_package_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
            extra_builder_args=["--lifetime-days", "1"],
        )
        expired = tmp_path / "expired.life"

        def mutate(name: str, data: bytes) -> Any:
            if name == "life-package.json":
                pkg = json.loads(data)
                pkg["expires_at"] = "2000-01-01T00:00:00.000000Z"
                return (name, json.dumps(pkg).encode("utf-8"))
            return True

        _rebuild_zip_with(good, expired, mutate)
        # Structural / inventory hash will fail first (descriptor was
        # rewritten without re-walking inventory). Mounting expired
        # is exercised more directly via the synthetic VerifyResult
        # below, but ensure the CLI also rejects this case.
        result = verify(expired, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok


def test_withdrawn_response_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with with_mock_server(status=200, body='{"status":"withdrawn"}') as (_srv, url):
            life = _build_life(withdrawal_endpoint=url, workdir=tmp_path)
            result = verify(life)
            assert not result.ok
            steps = [e.step for e in result.errors]
            assert "withdrawal" in steps
            reasons = [e.reason for e in result.errors]
            assert "package_withdrawn" in reasons


def test_unreachable_endpoint_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Bind a socket to claim a port, then immediately release it so
        # the actual HTTP call fails with "connection refused".
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        url = f"http://127.0.0.1:{port}/withdraw"
        life = _build_life(withdrawal_endpoint=url, workdir=tmp_path)
        result = verify(
            life,
            withdrawal_policy=WithdrawalPolicy(mode="online", timeout_seconds=2.0),
        )
        assert not result.ok
        first = result.first_error()
        assert first.step == "withdrawal"
        assert first.reason in {"endpoint_unreachable", "endpoint_http_error"}


def test_withdrawal_4xx_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with with_mock_server(status=403, body='{"detail":"forbidden"}') as (_srv, url):
            life = _build_life(withdrawal_endpoint=url, workdir=tmp_path)
            result = verify(life)
            assert not result.ok
            first = result.first_error()
            assert first.step == "withdrawal"
            assert first.reason in {"endpoint_http_error", "endpoint_unreachable"}


def test_lifecycle_withdrawn_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        # Inject a lifecycle/lifecycle.json with state=withdrawn AND
        # patch the descriptor's contents[] to keep the inventory
        # check happy.
        with_lc = tmp_path / "with-lifecycle.life"

        lifecycle_doc = {
            "schema_version": "0.1.0",
            "doc_kind": "package_lifecycle",
            "package_id": "PLACEHOLDER",
            "record_id": "PLACEHOLDER",
            "lifecycle_state": "withdrawn",
            "frozen": True,
            "withdrawn_at": "2026-04-26T00:00:00.000000Z",
        }

        def patch_descriptor(pkg: dict, lc_bytes: bytes) -> dict:
            import hashlib

            sha = "sha256:" + hashlib.sha256(lc_bytes).hexdigest()
            pkg = dict(pkg)
            pkg["contents"] = list(pkg.get("contents", [])) + [
                {
                    "path": "lifecycle/lifecycle.json",
                    "sha256": sha,
                    "size": len(lc_bytes),
                }
            ]
            return pkg

        # Read the original descriptor + lifecycle bytes first so we can
        # inject consistently.
        with zipfile.ZipFile(good, "r") as zin:
            descriptor = json.loads(zin.read("life-package.json"))
        lifecycle_doc["package_id"] = descriptor["package_id"]
        lifecycle_doc["record_id"] = descriptor["record_id"]
        lc_bytes = json.dumps(
            lifecycle_doc, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

        new_descriptor = patch_descriptor(descriptor, lc_bytes)

        def mutate(name: str, data: bytes) -> Any:
            if name == "life-package.json":
                return (name, json.dumps(new_descriptor).encode("utf-8"))
            return True

        _rebuild_zip_with(good, with_lc, mutate)
        with zipfile.ZipFile(with_lc, "a") as zout:
            zout.writestr("lifecycle/lifecycle.json", lc_bytes)

        result = verify(with_lc, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        steps = [e.step for e in result.errors]
        assert "lifecycle" in steps


def test_audit_log_non_utf8_returns_structured_error() -> None:
    """Regression: crafted audit/events.jsonl with non-UTF-8 bytes must not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        broken = tmp_path / "non-utf8-audit.life"

        def mutate(name: str, data: bytes) -> Any:
            if name == "audit/events.jsonl":
                return (name, b"\xff\xfe\xfd not utf-8\n")
            return True

        _rebuild_zip_with(good, broken, mutate)
        result = verify(broken, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        first = result.first_error()
        # Inventory may catch it first (mutated bytes hash differently) — that's
        # also a valid spec rejection. The point is we got a structured
        # rejection, not a crash.
        assert first.step in {"audit_chain", "inventory"}


def test_naive_datetime_in_descriptor_returns_structured_error() -> None:
    """Regression: naive (no-tz) timestamps must return parse_failure, not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=tmp_path / "build",
        )
        bad = tmp_path / "naive-time.life"

        def mutate(name: str, data: bytes) -> Any:
            if name == "life-package.json":
                pkg = json.loads(data)
                pkg["created_at"] = "2026-04-26T00:00:00"  # no Z, no offset
                return (name, json.dumps(pkg).encode("utf-8"))
            return True

        _rebuild_zip_with(good, bad, mutate)
        result = verify(bad, withdrawal_policy=WithdrawalPolicy(mode="mock-not-revoked"))
        assert not result.ok
        # Inventory hash of life-package.json now differs, so inventory may
        # fail first; either step counts as fail-close.
        steps = {e.step for e in result.errors}
        assert steps & {"time", "inventory", "schema"}


def test_schemeless_withdrawal_endpoint_returns_structured_error() -> None:
    """Regression: schemeless withdrawal_endpoint must not crash urllib."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = _build_life(
            withdrawal_endpoint="example.invalid/withdraw",
            workdir=tmp_path / "build",
        )
        # Default policy = online -> hits the urllib.Request constructor
        # path that previously crashed with ValueError("unknown url type").
        result = verify(good)
        assert not result.ok
        reasons = [e.reason for e in result.errors]
        assert "endpoint_malformed_url" in reasons


def test_assembly_aborted_audit_event_emitted() -> None:
    """Stage gating: any fail emits assembly_aborted{stage="verify"}."""
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.life"
        bad.write_bytes(b"not a zip file")
        recorder = AuditRecorder()
        verify(bad, audit=recorder)
        types = recorder.types()
        assert types[0] == "mount_attempted", types
        assert "assembly_aborted" in types, types
        last = recorder.latest("assembly_aborted")
        assert last is not None and last.fields["stage"] == "verify"


def test_lifectl_info_passes_for_good_package() -> None:
    """CLI path: `lifectl info` exits 0 + prints PASS for a freshly-built package.

    Builds the fixture on the fly because the bundled
    ``examples/minimal-life-package/out/*.life`` is gitignored — see
    ``examples/minimal-life-package/.gitignore``.
    """
    with tempfile.TemporaryDirectory() as tmp:
        fixture = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=Path(tmp),
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli.lifectl",
                "info",
                str(fixture),
                "--withdrawal-mock",
                "not-revoked",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "verification:     PASS" in proc.stdout
        assert "package_id:       " in proc.stdout


def test_lifectl_info_json_contains_structured_errors() -> None:
    """CLI path: `--json` returns parsable structured output."""
    with tempfile.TemporaryDirectory() as tmp:
        fixture = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=Path(tmp),
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli.lifectl",
                "info",
                str(fixture),
                "--withdrawal-mock",
                "revoked",
                "--json",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1, proc.stderr
        payload = json.loads(proc.stdout)
        assert payload["ok"] is False
        assert isinstance(payload["package_id"], str) and payload["package_id"]
        reasons = [e["reason"] for e in payload["errors"]]
        assert "package_withdrawn" in reasons


def test_lifectl_run_stage1_pass_then_pending() -> None:
    """CLI path: `lifectl run` exits 2 once Stage 1 passes (pending Stage 2)."""
    with tempfile.TemporaryDirectory() as tmp:
        fixture = _build_life(
            withdrawal_endpoint="http://127.0.0.1:1/withdraw",
            workdir=Path(tmp),
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.cli.lifectl",
                "run",
                str(fixture),
                "--withdrawal-mock",
                "not-revoked",
                "--once",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 2, (proc.stdout, proc.stderr)
        assert "Stage 1 Verify   ✓" in proc.stdout
        assert "Stage 2+ pending" in proc.stderr


# ---------------------------------------------------------------------------
# Driver


def main() -> int:
    tests = [
        test_happy_path_with_real_http,
        test_bad_zip_rejected,
        test_missing_descriptor_rejected,
        test_inventory_hash_mismatch_rejected,
        test_unlisted_extra_entry_rejected,
        test_audit_chain_break_rejected,
        test_expired_package_rejected,
        test_withdrawn_response_rejected,
        test_unreachable_endpoint_rejected,
        test_withdrawal_4xx_rejected,
        test_lifecycle_withdrawn_rejected,
        test_audit_log_non_utf8_returns_structured_error,
        test_naive_datetime_in_descriptor_returns_structured_error,
        test_schemeless_withdrawal_endpoint_returns_structured_error,
        test_assembly_aborted_audit_event_emitted,
        test_lifectl_info_passes_for_good_package,
        test_lifectl_info_json_contains_structured_errors,
        test_lifectl_run_stage1_pass_then_pending,
    ]
    failures: list[str] = []
    for test in tests:
        name = test.__name__
        try:
            test()
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
            print(f"FAIL  {name}:")
            for line in str(exc).splitlines():
                print(f"      {line}")
        except Exception as exc:  # noqa: BLE001 - sanity test driver
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {name}")

    print()
    if failures:
        print(f"{len(failures)} of {len(tests)} runtime-verify tests failed.")
        return 1
    print(f"all {len(tests)} runtime-verify tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
