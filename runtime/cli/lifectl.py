"""``lifectl`` — DLRS reference runtime CLI.

v0.9 sub-issue #120 laid down the scaffold; #121 wires Stage 1 Verify.
Stages 2-5 land in #122-#125; the e2e echo Provider + conformance
harness in #126.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runtime import LIFE_RUNTIME_PROTOCOL_VERSION, __version__
from runtime.audit import AuditRecorder
from runtime.verify import VerifyResult, WithdrawalPolicy, verify


_NOT_IMPLEMENTED_RUN_TAIL = (
    "Stage 2+ pending sub-issues #122-#126."
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lifectl",
        description=(
            "DLRS reference runtime CLI. Mounts a single `.life` archive end-to-end "
            "via the 5-stage assembly pipeline (Verify → Resolve → Assemble → Run "
            "→ Guard) defined in docs/LIFE_RUNTIME_STANDARD.md."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="print runtime version + protocol version and exit")

    info = sub.add_parser(
        "info",
        help="print a structured Stage 1 Verify report for a `.life` archive",
    )
    info.add_argument("life_path", type=Path, help="path to a `.life` archive")
    _add_verify_options(info)
    info.add_argument(
        "--json",
        action="store_true",
        help="emit a JSON document instead of human-readable text",
    )

    run = sub.add_parser("run", help="mount and run a `.life` archive end-to-end")
    run.add_argument("life_path", type=Path, help="path to a `.life` archive")
    run.add_argument(
        "--once",
        action="store_true",
        help="read one stdin line, process one turn, exit (test/CI use)",
    )
    run.add_argument(
        "--no-tty",
        action="store_true",
        help="non-interactive mode (no readline / no prompt)",
    )
    run.add_argument(
        "--poll-interval-override",
        type=float,
        default=None,
        metavar="SECONDS",
        help=(
            "override the Stage 5 watcher poll interval (test-only; spec mandates "
            "≥24h in production)"
        ),
    )
    _add_verify_options(run)

    return parser


def _add_verify_options(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--withdrawal-mock",
        choices=["not-revoked", "revoked", "unreachable", "malformed"],
        default=None,
        help=(
            "TEST ONLY: short-circuit the §2.5 withdrawal HTTP poll with a "
            "deterministic outcome. Production runtimes MUST omit this flag."
        ),
    )
    p.add_argument(
        "--withdrawal-timeout",
        type=float,
        default=10.0,
        help="HTTP timeout (seconds) for the §2.5 withdrawal pre-flight (default: 10)",
    )


def _withdrawal_policy_from_args(args: argparse.Namespace) -> WithdrawalPolicy:
    if args.withdrawal_mock is None:
        return WithdrawalPolicy(mode="online", timeout_seconds=args.withdrawal_timeout)
    return WithdrawalPolicy(
        mode=f"mock-{args.withdrawal_mock}",  # type: ignore[arg-type]
        timeout_seconds=args.withdrawal_timeout,
    )


def cmd_version() -> int:
    print(f"lifectl {__version__} (life-runtime v{LIFE_RUNTIME_PROTOCOL_VERSION})")
    return 0


def _verify_result_to_dict(result: VerifyResult) -> dict:
    return {
        "ok": result.ok,
        "life_path": str(result.life_path),
        "package_id": result.package_id,
        "schema_version": result.schema_version,
        "mode": result.mode,
        "record_id": result.record_id,
        "created_at": result.created_at,
        "expires_at": result.expires_at,
        "runtime_compatibility": result.runtime_compatibility,
        "lifecycle_state": result.lifecycle_state,
        "audit_chain_length": result.audit_chain_length,
        "audit_event_ref": result.audit_event_ref,
        "inventory_entries_verified": result.inventory_entries_verified,
        "forbidden_uses_count": len(result.forbidden_uses),
        "errors": [e.to_dict() for e in result.errors],
        "warnings": result.warnings,
    }


def _print_human_report(result: VerifyResult) -> None:
    out = sys.stdout
    print(f"life_path:        {result.life_path}", file=out)
    print(f"package_id:       {result.package_id}", file=out)
    print(f"schema_version:   {result.schema_version}", file=out)
    print(f"mode:             {result.mode}", file=out)
    print(f"record_id:        {result.record_id}", file=out)
    print(f"created_at:       {result.created_at}", file=out)
    print(f"expires_at:       {result.expires_at}", file=out)
    print(
        f"runtime_compat:   {', '.join(result.runtime_compatibility) or '(none)'}",
        file=out,
    )
    print(f"lifecycle_state:  {result.lifecycle_state}", file=out)
    print(f"audit_chain_len:  {result.audit_chain_length}", file=out)
    print(f"audit_event_ref:  {result.audit_event_ref}", file=out)
    print(
        f"inventory_verified: {result.inventory_entries_verified} entries",
        file=out,
    )
    print(f"forbidden_uses:   {len(result.forbidden_uses)} key(s)", file=out)
    if result.warnings:
        print("warnings:", file=out)
        for w in result.warnings:
            print(f"  - {w}", file=out)
    verdict = "PASS" if result.ok else "FAIL"
    print(f"verification:     {verdict}", file=out)
    if not result.ok:
        print("errors:", file=sys.stderr)
        for err in result.errors:
            line = f"  [{err.step}] {err.reason}"
            if err.detail:
                line += f" ({err.detail})"
            print(line, file=sys.stderr)


def cmd_info(args: argparse.Namespace) -> int:
    if not args.life_path.exists():
        print(f"life_path does not exist: {args.life_path}", file=sys.stderr)
        return 2

    audit = AuditRecorder()
    result = verify(
        args.life_path,
        audit=audit,
        withdrawal_policy=_withdrawal_policy_from_args(args),
    )
    if args.json:
        print(
            json.dumps(_verify_result_to_dict(result), indent=2, ensure_ascii=False)
        )
    else:
        _print_human_report(result)
    return 0 if result.ok else 1


def cmd_run(args: argparse.Namespace) -> int:
    audit = AuditRecorder()
    result = verify(
        args.life_path,
        audit=audit,
        withdrawal_policy=_withdrawal_policy_from_args(args),
    )
    if not result.ok:
        first = result.first_error()
        if first is not None:
            print(
                f"Stage 1 Verify FAIL [{first.step}] {first.reason}"
                + (f" ({first.detail})" if first.detail else ""),
                file=sys.stderr,
            )
        else:  # pragma: no cover - defensive
            print("Stage 1 Verify FAIL", file=sys.stderr)
        return 1

    print("Stage 1 Verify   ✓", file=sys.stdout)
    print(f"package_id={result.package_id} mode={result.mode} "
          f"lifecycle_state={result.lifecycle_state}", file=sys.stdout)
    if result.warnings:
        for w in result.warnings:
            print(f"warning: {w}", file=sys.stdout)
    print(_NOT_IMPLEMENTED_RUN_TAIL, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        return cmd_version()
    if args.command == "info":
        return cmd_info(args)
    if args.command == "run":
        return cmd_run(args)

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
