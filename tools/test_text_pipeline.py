#!/usr/bin/env python3
"""Tests for ``pipelines.text`` (cleaning + redaction).

Two layers:

1. Unit tests for :func:`pipelines.text.cleaning.normalise` and
   :func:`pipelines.text.cleaning.redact` so regressions land here first.
2. End-to-end CLI test that runs ``run_pipeline.py text`` against a
   synthetic record (transcript.json input) and validates the produced
   descriptor against ``schemas/derived-asset.schema.json``.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.text.cleaning import normalise, redact  # noqa: E402

SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _unit_tests_normalise(errors: list[str]) -> None:
    cases = [
        # (label, input, expected)
        ("nfkc fullwidth ABC", "ＡＢＣ", "ABC"),
        ("strip BOM and zero-width", "hello\ufeff\u200bworld", "helloworld"),
        ("CRLF -> LF", "a\r\nb\r\nc", "a\nb\nc"),
        ("collapse horizontal ws", "a    b\tc\u3000d", "a b c d"),
        ("trailing whitespace before newline", "line1   \nline2", "line1\nline2"),
        ("collapse 3+ newlines", "p1\n\n\n\np2", "p1\n\np2"),
        ("trim outer whitespace", "  hello  ", "hello"),
    ]
    for label, src, expected in cases:
        got = normalise(src)
        if got != expected:
            errors.append(f"normalise[{label}]: expected {expected!r} got {got!r}")


def _unit_tests_redact(errors: list[str]) -> None:
    # Each tuple is (label, input, must_contain_kinds, must_redact_substrings_gone).
    cases = [
        ("email", "contact me at alice@example.com please", ["email"], ["alice@example.com"]),
        (
            "chinese mobile",
            "我的电话是 13912345678 谢谢",
            ["phone_cn"],
            ["13912345678"],
        ),
        (
            "chinese id",
            "ID: 110101199001011234",
            ["id_cn"],
            ["110101199001011234"],
        ),
        (
            "ipv4",
            "router at 192.168.0.1 reachable",
            ["ipv4"],
            ["192.168.0.1"],
        ),
        (
            "credit card 16 digits",
            "card 4111 1111 1111 1111 expires 12/30",
            ["credit_card_like"],
            ["4111 1111 1111 1111"],
        ),
        (
            "url with creds",
            "fetch https://user:pw@example.com/path",
            ["url_with_credentials"],
            ["user:pw@example.com"],
        ),
        (
            "no false positive on plain digits",
            "year 2026, sample size 30",
            [],
            [],
        ),
    ]
    for label, src, expected_kinds, must_be_gone in cases:
        cleaned, redactions = redact(src)
        got_kinds = sorted({r.kind for r in redactions})
        for k in expected_kinds:
            if k not in got_kinds:
                errors.append(
                    f"redact[{label}]: expected kind {k!r} in {got_kinds}; cleaned={cleaned!r}"
                )
        if not expected_kinds and redactions:
            errors.append(
                f"redact[{label}]: expected NO redactions but got {got_kinds}; cleaned={cleaned!r}"
            )
        for substr in must_be_gone:
            if substr in cleaned:
                errors.append(
                    f"redact[{label}]: original substring {substr!r} still present in cleaned output"
                )
        # Redactions must NOT echo the original sensitive substring.
        for r in redactions:
            for substr in must_be_gone:
                if substr in r.replacement or substr in r.kind:
                    errors.append(
                        f"redact[{label}]: redaction record leaks original substring"
                    )


def _make_synthetic_record(root: Path, transcript_text: list[str]) -> Path:
    record = root / "dlrs_test_text_001"
    derived_asr = record / "derived" / "asr"
    derived_asr.mkdir(parents=True, exist_ok=True)
    transcript_path = derived_asr / "voice_master.transcript.json"
    transcript_path.write_text(
        json.dumps(
            {
                "audio_path": "(synthetic)",
                "audio_sha256": "sha256:" + "a" * 64,
                "duration_seconds": 0.0,
                "language": "zh",
                "language_confidence": None,
                "backend": "dummy",
                "model_id": "dummy:small",
                "segments": [
                    {"index": i, "start": 0.0, "end": 0.0, "text": line}
                    for i, line in enumerate(transcript_text)
                ],
                "metadata": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (record / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "dlrs-manifest/1.0",
                "record_id": "dlrs_test_text_001",
                "created_at": "2026-04-26T07:00:00Z",
                "artifacts": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return record


def _e2e_test(errors: list[str]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.append("jsonschema not installed; install via tools/requirements.txt")
        return

    transcript_lines = [
        "我的电话是 13912345678",
        "联系邮箱 alice@example.com",
        "ＡＢＣ\u3000DEF",  # to exercise normalise via the transcript path
    ]
    with tempfile.TemporaryDirectory() as tmp:
        record = _make_synthetic_record(Path(tmp), transcript_lines)
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "text",
            "--record",
            str(record),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            errors.append(f"run_pipeline.py text exited {proc.returncode}: {proc.stderr.strip()}")
            return

        derived = record / "derived" / "text"
        clean_path = derived / "voice_master.clean.txt"
        red_path = derived / "voice_master.redactions.json"
        desc_path = derived / "voice_master.clean.descriptor.json"

        for p in (clean_path, red_path, desc_path):
            _assert(p.exists(), f"missing output {p}", errors)

        if clean_path.exists():
            cleaned = clean_path.read_text(encoding="utf-8")
            _assert("13912345678" not in cleaned, "phone leaked into clean.txt", errors)
            _assert("alice@example.com" not in cleaned, "email leaked into clean.txt", errors)
            _assert("ABC DEF" in cleaned, "NFKC normalisation didn't reach the clean output", errors)

        if red_path.exists():
            payload = json.loads(red_path.read_text(encoding="utf-8"))
            kinds = sorted({r["kind"] for r in payload.get("redactions", [])})
            _assert("phone_cn" in kinds, f"phone_cn not in redactions: {kinds}", errors)
            _assert("email" in kinds, f"email not in redactions: {kinds}", errors)
            _assert(
                payload.get("summary", {}).get("total", 0) >= 2,
                f"redactions summary.total too low: {payload.get('summary')}",
                errors,
            )

        if desc_path.exists():
            d = json.loads(desc_path.read_text(encoding="utf-8"))
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            schema_errors = sorted(Draft202012Validator(schema).iter_errors(d), key=lambda e: e.path)
            for se in schema_errors:
                errors.append(
                    f"text descriptor schema error at {'/'.join(map(str, se.path)) or '<root>'}: {se.message}"
                )
            _assert(d.get("pipeline") == "text", "descriptor.pipeline != text", errors)
            _assert(
                d.get("output", {}).get("path", "").startswith("derived/text/"),
                "descriptor.output.path doesn't start with derived/text/",
                errors,
            )


def main() -> int:
    errors: list[str] = []
    _unit_tests_normalise(errors)
    _unit_tests_redact(errors)
    _e2e_test(errors)

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"test_text_pipeline: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("test_text_pipeline: normalise + redact + end-to-end OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
