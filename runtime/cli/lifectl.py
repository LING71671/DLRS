"""``lifectl`` — DLRS reference runtime CLI.

v0.9 sub-issue #120 (scaffold). Concrete assembly logic lands in #121-#126.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from runtime import LIFE_RUNTIME_PROTOCOL_VERSION, __version__

_NOT_IMPLEMENTED_INFO = (
    "lifectl info: not yet implemented (v0.9 sub-issue #121 — Stage 1 Verify)."
)
_NOT_IMPLEMENTED_RUN = (
    "lifectl run: not yet implemented (v0.9 sub-issues #121-#126 — full 5-stage "
    "assembly)."
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
        help="print a structured verification report for a `.life` archive (Stage 1 only)",
    )
    info.add_argument("life_path", type=Path, help="path to a `.life` archive")

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

    return parser


def cmd_version() -> int:
    print(f"lifectl {__version__} (life-runtime v{LIFE_RUNTIME_PROTOCOL_VERSION})")
    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED_INFO, file=sys.stderr)
    return 2


def cmd_run(_args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED_RUN, file=sys.stderr)
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
