#!/usr/bin/env python3
"""Sanity tests for ``schemas/life-package.schema.json``.

Mirrors the structure of ``test_memory_atom_schema.py`` and
``test_entity_graph_schema.py``: build a known-good descriptor for each
mode, then mutate it along every dimension the schema is supposed to
police.  The example builder shipping in #83 uses the same schema to
validate every emitted ``life-package.json``, so these cases double as
pre-flight checks for that builder.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "life-package.schema.json"


def _good_pointer_pkg() -> dict:
    return {
        "schema_version": "0.1.0",
        "package_id": "01HW9PQR8XKZA9E2D5VBNRTFCZ",
        "mode": "pointer",
        "record_id": "dlrs_94f1c9b8_lin-example",
        "created_at": "2026-04-26T12:00:00Z",
        "expires_at": "2027-04-26T12:00:00Z",
        "issued_by": {
            "role": "self",
            "identifier": "lin-example",
            "signature_ref": "consent/signature.bin",
        },
        "consent_evidence_ref": "consent/consent.md",
        "verification_level": "self_attested",
        "withdrawal_endpoint": "https://example.org/withdrawal/dlrs_94f1c9b8_lin-example",
        "runtime_compatibility": ["dlrs-runtime-v0"],
        "ai_disclosure": "visible_label_required",
        "forbidden_uses": ["impersonation_for_fraud", "political_endorsement"],
        "audit_event_ref": "audit/events.jsonl#L42",
        "contents": [
            {
                "path": "manifest.json",
                "sha256": "sha256:" + "a" * 64,
                "size": 1234,
            },
            {
                "path": "consent/consent.md",
                "sha256": "sha256:" + "b" * 64,
                "size": 567,
            },
            {
                "path": "audit/events.jsonl",
                "sha256": "sha256:" + "c" * 64,
                "size": 8901,
            },
            {
                "path": "pointers/voice.pointer.json",
                "sha256": "sha256:" + "d" * 64,
                "size": 256,
            },
        ],
    }


def _good_encrypted_pkg() -> dict:
    pkg = _good_pointer_pkg()
    pkg["mode"] = "encrypted"
    pkg["contents"] = [
        {
            "path": "manifest.json",
            "sha256": "sha256:" + "a" * 64,
            "size": 1234,
        },
        {
            "path": "consent/consent.md",
            "sha256": "sha256:" + "b" * 64,
            "size": 567,
        },
        {
            "path": "audit/events.jsonl",
            "sha256": "sha256:" + "c" * 64,
            "size": 8901,
        },
        {
            "path": "encrypted/" + "d" * 64 + ".bin",
            "sha256": "sha256:" + "e" * 64,
            "size": 18483712,
        },
        {
            "path": "encrypted/wrapped-key-1.bin",
            "sha256": "sha256:" + "f" * 64,
            "size": 256,
        },
    ]
    pkg["encryption"] = {
        "algorithm": "AES-256-GCM",
        "key_distribution": "external_kms",
        "recipients": [
            {
                "kid": "kms://example/key-1",
                "wrapped_key_ref": "encrypted/wrapped-key-1.bin",
            }
        ],
        "assets": [
            {
                "logical_path": "voice/master.wav",
                "blob_path": "encrypted/" + "d" * 64 + ".bin",
                "plaintext_sha256": "sha256:" + "7" * 64,
                "nonce": "AAECAwQFBgcICQoLDA==",
                "auth_tag": "EBESExQVFhcYGRobHB0eHw==",
            }
        ],
    }
    return pkg


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    cases: list[tuple[str, dict, bool]] = []

    # --- happy paths -----------------------------------------------------
    cases.append(("good pointer-mode package", _good_pointer_pkg(), True))
    cases.append(("good encrypted-mode package", _good_encrypted_pkg(), True))

    with_notes = _good_pointer_pkg()
    with_notes["notes"] = "Built from diary-only subset for offline runtime smoke test."
    cases.append(("pointer pkg with optional notes", with_notes, True))

    memorial = _good_pointer_pkg()
    memorial["verification_level"] = "memorial_authorized"
    memorial["issued_by"]["role"] = "memorial_executor"
    cases.append(("memorial-authorised pkg with executor role", memorial, True))

    # --- enum / const guards --------------------------------------------
    bad_schema_version = _good_pointer_pkg()
    bad_schema_version["schema_version"] = "0.2.0"
    cases.append(("schema_version != 0.1.0", bad_schema_version, False))

    bad_mode = _good_pointer_pkg()
    bad_mode["mode"] = "mixed"
    cases.append(("mode outside enum", bad_mode, False))

    bad_verification = _good_pointer_pkg()
    bad_verification["verification_level"] = "court_order"
    cases.append(("verification_level outside enum", bad_verification, False))

    bad_role = _good_pointer_pkg()
    bad_role["issued_by"]["role"] = "next_of_kin"
    cases.append(("issued_by.role outside enum", bad_role, False))

    bad_disclosure = _good_pointer_pkg()
    bad_disclosure["ai_disclosure"] = "invisible_only"
    cases.append(("ai_disclosure outside enum", bad_disclosure, False))

    # --- ULID guard ------------------------------------------------------
    short_ulid = _good_pointer_pkg()
    short_ulid["package_id"] = "01HW9PQR8XKZA9E2D5VBNR"  # 22 chars
    cases.append(("package_id too short for ULID", short_ulid, False))

    lower_ulid = _good_pointer_pkg()
    lower_ulid["package_id"] = "01hw9pqr8xkza9e2d5vbnrtfcz"
    cases.append(("package_id lowercase (Crockford rejects)", lower_ulid, False))

    bad_alphabet_ulid = _good_pointer_pkg()
    bad_alphabet_ulid["package_id"] = "01HW9PQR8XKZA9E2D5VBNRTFCI"  # I not in Crockford
    cases.append(("package_id uses I (not in Crockford)", bad_alphabet_ulid, False))

    # --- record_id pattern ----------------------------------------------
    bad_record = _good_pointer_pkg()
    bad_record["record_id"] = "94f1c9b8_lin-example"
    cases.append(("record_id missing dlrs_ prefix", bad_record, False))

    # --- audit_event_ref pattern ----------------------------------------
    bad_ref = _good_pointer_pkg()
    bad_ref["audit_event_ref"] = "audit/events.jsonl:42"
    cases.append(("audit_event_ref wrong separator", bad_ref, False))

    bad_ref2 = _good_pointer_pkg()
    bad_ref2["audit_event_ref"] = "audit/events.jsonl#L0"
    cases.append(("audit_event_ref line-zero", bad_ref2, False))

    bad_ref3 = _good_pointer_pkg()
    bad_ref3["audit_event_ref"] = "events.jsonl#L42"
    cases.append(("audit_event_ref missing audit/ prefix", bad_ref3, False))

    # --- contents path / sha256 / size guards ---------------------------
    abs_path = _good_pointer_pkg()
    abs_path["contents"][0]["path"] = "/manifest.json"
    cases.append(("contents path absolute", abs_path, False))

    dotdot_path = _good_pointer_pkg()
    dotdot_path["contents"][0]["path"] = "../escape.json"
    cases.append(("contents path traverses ..", dotdot_path, False))

    bad_sha = _good_pointer_pkg()
    bad_sha["contents"][0]["sha256"] = "md5:" + "a" * 64
    cases.append(("contents sha256 wrong algorithm prefix", bad_sha, False))

    short_sha = _good_pointer_pkg()
    short_sha["contents"][0]["sha256"] = "sha256:" + "a" * 32
    cases.append(("contents sha256 too short", short_sha, False))

    neg_size = _good_pointer_pkg()
    neg_size["contents"][0]["size"] = -1
    cases.append(("contents size negative", neg_size, False))

    empty_contents = _good_pointer_pkg()
    empty_contents["contents"] = []
    cases.append(("contents empty array", empty_contents, False))

    upper_sha = _good_pointer_pkg()
    upper_sha["contents"][0]["sha256"] = "sha256:" + "A" * 64
    cases.append(("contents sha256 accepts uppercase hex (case-insensitive)", upper_sha, True))

    mixed_sha = _good_pointer_pkg()
    mixed_sha["contents"][0]["sha256"] = "sha256:" + ("aB" * 32)
    cases.append(("contents sha256 accepts mixed-case hex", mixed_sha, True))

    upper_plaintext_sha = _good_encrypted_pkg()
    upper_plaintext_sha["encryption"]["assets"][0]["plaintext_sha256"] = "sha256:" + "F" * 64
    cases.append(("encryption plaintext_sha256 accepts uppercase hex", upper_plaintext_sha, True))

    # --- runtime_compatibility / forbidden_uses guards ------------------
    empty_runtime = _good_pointer_pkg()
    empty_runtime["runtime_compatibility"] = []
    cases.append(("runtime_compatibility empty", empty_runtime, False))

    empty_forbidden = _good_pointer_pkg()
    empty_forbidden["forbidden_uses"] = []
    # Empty array is permitted (strongly discouraged but not schema-blocked).
    cases.append(("forbidden_uses empty array (allowed)", empty_forbidden, True))

    # withdrawal_endpoint format=uri is annotation-only in this repo's
    # validator setup (matches every other DLRS schema; no FormatChecker
    # is wired in); we therefore don't assert URI shape here. Pattern-
    # based shape checks live in the example builder (#83) instead.

    # --- mode/encryption conditional ------------------------------------
    encrypted_no_block = _good_encrypted_pkg()
    encrypted_no_block.pop("encryption")
    cases.append(("encrypted mode without encryption block", encrypted_no_block, False))

    pointer_with_block = _good_pointer_pkg()
    pointer_with_block["encryption"] = {
        "algorithm": "AES-256-GCM",
        "key_distribution": "external_kms",
        "recipients": [{"kid": "k", "wrapped_key_ref": "encrypted/k.bin"}],
        "assets": [
            {
                "logical_path": "x",
                "blob_path": "encrypted/x.bin",
                "plaintext_sha256": "sha256:" + "0" * 64,
                "nonce": "AAA=",
                "auth_tag": "BBB=",
            }
        ],
    }
    cases.append(("pointer mode with encryption block", pointer_with_block, False))

    # --- encryption sub-object guards -----------------------------------
    bad_algo = _good_encrypted_pkg()
    bad_algo["encryption"]["algorithm"] = "DES"
    cases.append(("encryption.algorithm not AEAD", bad_algo, False))

    bad_kdist = _good_encrypted_pkg()
    bad_kdist["encryption"]["key_distribution"] = "embedded"
    cases.append(("encryption.key_distribution outside enum", bad_kdist, False))

    no_recipients = _good_encrypted_pkg()
    no_recipients["encryption"]["recipients"] = []
    cases.append(("encryption.recipients empty", no_recipients, False))

    bad_wrapped = _good_encrypted_pkg()
    bad_wrapped["encryption"]["recipients"][0]["wrapped_key_ref"] = "wrapped-key-1.bin"
    cases.append(("recipients[].wrapped_key_ref not under encrypted/", bad_wrapped, False))

    bad_blob_path = _good_encrypted_pkg()
    bad_blob_path["encryption"]["assets"][0]["blob_path"] = "blobs/x.bin"
    cases.append(("assets[].blob_path not under encrypted/", bad_blob_path, False))

    # --- memorial conditional (bi-directional) --------------------------
    memorial_wrong_role = _good_pointer_pkg()
    memorial_wrong_role["verification_level"] = "memorial_authorized"
    memorial_wrong_role["issued_by"]["role"] = "self"
    cases.append(("memorial verification but role=self", memorial_wrong_role, False))

    executor_wrong_verification = _good_pointer_pkg()
    executor_wrong_verification["issued_by"]["role"] = "memorial_executor"
    executor_wrong_verification["verification_level"] = "self_attested"
    cases.append(("memorial_executor role but verification_level=self_attested", executor_wrong_verification, False))

    executor_wrong_verification_3p = _good_pointer_pkg()
    executor_wrong_verification_3p["issued_by"]["role"] = "memorial_executor"
    executor_wrong_verification_3p["verification_level"] = "third_party_verified"
    cases.append(("memorial_executor role but verification_level=third_party_verified", executor_wrong_verification_3p, False))

    # --- additionalProperties guard -------------------------------------
    extra = _good_pointer_pkg()
    extra["random_extra"] = 1
    cases.append(("unknown top-level field", extra, False))

    extra_issued = _good_pointer_pkg()
    extra_issued["issued_by"]["legal_jurisdiction"] = "DE"
    cases.append(("unknown issued_by field", extra_issued, False))

    # --- missing required ------------------------------------------------
    for required_field in [
        "schema_version",
        "package_id",
        "mode",
        "record_id",
        "created_at",
        "expires_at",
        "issued_by",
        "consent_evidence_ref",
        "verification_level",
        "withdrawal_endpoint",
        "runtime_compatibility",
        "ai_disclosure",
        "forbidden_uses",
        "audit_event_ref",
        "contents",
    ]:
        missing = _good_pointer_pkg()
        missing.pop(required_field)
        cases.append((f"missing required field {required_field}", missing, False))

    # --- run -------------------------------------------------------------
    failures = 0
    for name, doc, expect_valid in cases:
        errors = list(validator.iter_errors(doc))
        is_valid = not errors
        if is_valid != expect_valid:
            failures += 1
            print(f"FAIL  {name}: expected valid={expect_valid} got valid={is_valid}")
            for e in errors[:3]:
                print(f"      - {e.message}")
        else:
            print(f"OK    {name}")

    if failures:
        print(f"\ntest_life_package_schema: {failures}/{len(cases)} case(s) failed")
        return 1
    print(f"\ntest_life_package_schema: all {len(cases)} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
