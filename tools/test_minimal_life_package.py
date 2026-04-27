#!/usr/bin/env python3
"""End-to-end test for examples/minimal-life-package/.

Copies the example to a temp directory (so the source audit log isn't
mutated), runs build_life.sh in deterministic mode, and verifies:

- Build exits 0 and writes <out>/<package_id>.life.
- Zip member set is what we expect (manifest, consent, audit, policy,
  pointers, derived/* and a top-level life-package.json).
- life-package.json validates against schemas/life-package.schema.json.
- contents[] inventory matches sha256 + size of every file in the zip
  (excluding life-package.json itself).
- audit/events.jsonl has 2 lines and the prev_hash chain links them.
- The line referenced by audit_event_ref is a `package_emitted` event
  whose metadata.package_id matches life-package.json::package_id.
- Deterministic mode produces a stable package_id and identical
  life-package.json bytes across two consecutive builds.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "minimal-life-package"
SCHEMA_PATH = ROOT / "schemas" / "life-package.schema.json"
EXPECTED_PACKAGE_ID = "01HW9PQR8XKZA9E2D5VBNRTFCZ"


def _stage_copy(tmpdir: Path) -> Path:
    """Copy the example record into a tmp dir so the source audit
    chain doesn't grow as we re-run the build."""
    dst = tmpdir / "minimal-life-package"
    shutil.copytree(EXAMPLE_DIR, dst, ignore=shutil.ignore_patterns("out"))
    return dst


def _run_build(staged: Path) -> Path:
    out_dir = staged / "out"
    env = os.environ.copy()
    env["DLRS_LIFE_DETERMINISTIC"] = "1"
    env["DLRS_REPO_ROOT"] = str(ROOT)
    res = subprocess.run(
        ["bash", str(staged / "build_life.sh")],
        env=env,
        cwd=str(staged),
        check=True,
        capture_output=True,
        text=True,
    )
    print(res.stdout, end="")
    if res.stderr:
        print(res.stderr, file=sys.stderr, end="")
    life_files = list(out_dir.glob("*.life"))
    assert len(life_files) == 1, f"expected one .life output, got {life_files}"
    return life_files[0]


def _sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _verify_descriptor_against_zip(zf: zipfile.ZipFile, descriptor: dict) -> None:
    member_paths = {m for m in zf.namelist()}
    assert "life-package.json" in member_paths, "life-package.json missing from zip"

    listed = {entry["path"] for entry in descriptor["contents"]}
    actual_excluding_self = member_paths - {"life-package.json"}
    assert (
        listed == actual_excluding_self
    ), f"contents[] mismatch with zip members: in_descriptor_only={listed - actual_excluding_self}, in_zip_only={actual_excluding_self - listed}"

    by_path = {entry["path"]: entry for entry in descriptor["contents"]}
    for path in actual_excluding_self:
        body = zf.read(path)
        expected = by_path[path]
        assert (
            _sha256_bytes(body) == expected["sha256"]
        ), f"sha256 mismatch for {path}: descriptor={expected['sha256']}, actual={_sha256_bytes(body)}"
        assert (
            len(body) == expected["size"]
        ), f"size mismatch for {path}: descriptor={expected['size']}, actual={len(body)}"


def _verify_audit_chain(zf: zipfile.ZipFile, descriptor: dict) -> None:
    audit_text = zf.read("audit/events.jsonl").decode("utf-8")
    lines = [ln for ln in audit_text.splitlines() if ln.strip()]
    assert len(lines) == 2, f"expected 2 audit events, got {len(lines)}"

    events = [json.loads(ln) for ln in lines]
    assert events[0]["prev_hash"] is None, "first event must have prev_hash=null"
    assert events[1]["prev_hash"] == events[0]["hash"], (
        "second event prev_hash must equal first event hash; chain is broken"
    )
    # Recompute first event hash to ensure the seed line was not mutated.
    canonical0 = json.dumps(
        {k: v for k, v in events[0].items() if k != "hash"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert (
        "sha256:" + hashlib.sha256(canonical0.encode("utf-8")).hexdigest()
        == events[0]["hash"]
    ), "first audit event hash does not match canonical recomputation"

    ref = descriptor["audit_event_ref"]
    assert ref == "audit/events.jsonl#L2", f"expected audit_event_ref=audit/events.jsonl#L2, got {ref}"
    pe = events[1]
    assert pe["event_type"] == "package_emitted"
    assert pe["actor_role"] == "system"
    assert pe["metadata"]["package_id"] == descriptor["package_id"]


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    with tempfile.TemporaryDirectory() as tmp_str:
        tmpdir = Path(tmp_str)
        staged_a = _stage_copy(tmpdir / "a")
        life_a = _run_build(staged_a)

        with zipfile.ZipFile(life_a) as zf:
            descriptor = json.loads(zf.read("life-package.json").decode("utf-8"))
            validator.validate(descriptor)

            assert descriptor["schema_version"] == "0.1.0"
            assert descriptor["mode"] == "pointer"
            assert descriptor["package_id"] == EXPECTED_PACKAGE_ID
            assert descriptor["record_id"] == "dlrs_EXAMPLE_minimal_life"
            assert descriptor["verification_level"] == "self_attested"
            assert descriptor["ai_disclosure"] == "visible_label_required"
            assert "impersonation_for_fraud" in descriptor["forbidden_uses"]
            assert "encryption" not in descriptor, "pointer mode must not have encryption block"

            # v0.8 tier block: present and well-formed by default.
            assert "tier" in descriptor, "v0.8 builder must emit a tier block"
            t = descriptor["tier"]
            assert isinstance(t["score"], int) and 0 <= t["score"] <= 100
            assert t["level"] in {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"}
            assert t["computed_by"].startswith("tools/build_life_package.py@")
            assert "@" in t["computed_by"]
            for dim in ("identity_verification", "asset_completeness", "consent_completeness",
                        "detail_level", "audit_chain_strength", "jurisdiction_clarity"):
                assert dim in t["dimensions"], f"tier.dimensions missing {dim}"

            _verify_descriptor_against_zip(zf, descriptor)
            _verify_audit_chain(zf, descriptor)

        # Determinism check: a second fresh build from the same source should
        # produce a byte-identical life-package.json (same package_id, same
        # contents inventory ordering and hashes).
        staged_b = _stage_copy(tmpdir / "b")
        life_b = _run_build(staged_b)
        with zipfile.ZipFile(life_a) as za, zipfile.ZipFile(life_b) as zb:
            desc_a = za.read("life-package.json")
            desc_b = zb.read("life-package.json")
            assert (
                desc_a == desc_b
            ), "life-package.json bytes differ between two deterministic builds"

    print("test_minimal_life_package: OK (descriptor valid, contents inventory matches, audit chain links, deterministic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
