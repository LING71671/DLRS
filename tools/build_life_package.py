#!/usr/bin/env python3
"""Build a `.life` archive from a DLRS source record.

Implements the authoring workflow defined in
`docs/LIFE_FILE_STANDARD.md` §5 for `life-format v0.1.0`:

    1. Stage the source record subset that goes into the .life.
    2. Append a `package_emitted` audit event to the source
       record's `audit/events.jsonl` (v0.4 hash chain).
    3. Copy the (now-updated) audit log into the staged .life.
    4. Compute the sha256 inventory of every staged regular file
       except the soon-to-be-written `life-package.json`.
    5. Write `life-package.json` whose `audit_event_ref` points at
       the line of the `package_emitted` event inside the *bundled*
       audit log.
    6. Validate the descriptor against
       `schemas/life-package.schema.json` (Draft 2020-12).
    7. Zip the staged tree (deterministic ordering) into
       `<output_dir>/<package_id>.life`.

This v0.1 builder only emits **pointer-mode** packages
(`mode: "pointer"`). Encrypted-mode packaging (`mode: "encrypted"`,
AES-256-GCM minimum) is part of the schema but is deferred to a
later sub-issue with the actual KMS plumbing — the builder will
refuse the operation if `--encrypted-mode` is passed.

The builder does NOT touch the source record outside appending
exactly one event to `audit/events.jsonl`. To rebuild against the
same source record without growing the audit chain, copy the
source record to a temp directory first; the test driver
(`tools/test_minimal_life_package.py`) does exactly this.

Determinism
-----------
Pass `--deterministic` (or set ``DLRS_LIFE_DETERMINISTIC=1``) to:
- pin `package_id` to a fixed Crockford-base32 ULID,
- pin `created_at` / `expires_at` / audit timestamp to fixed
  values,
- skip ULID/UUID randomness in the audit emitter.

Otherwise the builder generates a fresh ULID and uses
`datetime.now(timezone.utc)`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import secrets
import shutil
import string
import sys
import zipfile
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - dep installed via tools/requirements.txt
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "life-package.schema.json"

# Crockford base32 alphabet used by ULIDs.
_CROCKFORD = string.digits + "ABCDEFGHJKMNPQRSTVWXYZ"

# Pinned values when running in deterministic mode (env or CLI flag).
_DET_PACKAGE_ID = "01HW9PQR8XKZA9E2D5VBNRTFCZ"
_DET_EVENT_ID = "01HW9PQR8XKZA9E2D5VBNRTFCD"
_DET_CREATED_AT = "2026-04-26T00:00:00.000000Z"
_DET_EXPIRES_AT = "2027-04-26T00:00:00.000000Z"


def _is_deterministic(cli_flag: bool) -> bool:
    return cli_flag or os.environ.get("DLRS_LIFE_DETERMINISTIC") == "1"


def _new_ulid() -> str:
    """Generate a Crockford-base32 ULID (26 chars). Random component only;
    the first 10 chars are the time component but the schema only
    constrains the full pattern, not the embedded timestamp."""
    return "".join(secrets.choice(_CROCKFORD) for _ in range(26))


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
            size += len(chunk)
    return "sha256:" + h.hexdigest(), size


def _canonical_dump(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# -------- v0.8 tier auto-compute -----------------------------------------
#
# These tables and weights mirror the normative definitions in
# `docs/LIFE_TIER_SPEC.md` §3–§5 and `schemas/tier.schema.json`. The
# builder computes the tier block deterministically from package
# contents + CLI-supplied hints. Hand-rolled tier blocks are forbidden
# (the schema rejects `computed_by` without a `@` separator); callers
# MUST let the builder write this field.

# Ordered dimension enums (low → high). Copied verbatim from the
# schema's enum arrays so any divergence is a test-visible bug.
_TIER_ENUMS: dict[str, list[str]] = {
    "identity_verification": ["unverified", "self_attested", "email_verified", "id_verified", "kyc_verified", "notarized"],
    "asset_completeness":    ["minimal", "partial", "standard", "comprehensive", "archive_grade"],
    "consent_completeness":  ["none", "text_only", "signed", "notarized", "multi_party_attested"],
    "detail_level":          ["low_fidelity", "medium", "high_fidelity", "cinematic"],
    "audit_chain_strength":  ["minimal", "linked", "signed_chain", "notarized_chain"],
    "jurisdiction_clarity":  ["unspecified", "declared", "cross_validated", "court_recognized"],
}

# Weights from the spec §4.1. identity and consent are doubled.
_TIER_WEIGHTS: dict[str, int] = {
    "identity_verification": 2,
    "consent_completeness":  2,
    "asset_completeness":    1,
    "detail_level":          1,
    "audit_chain_strength":  1,
    "jurisdiction_clarity":  1,
}

# Score → (level, name, glyph). Ranges are inclusive on both ends and
# exactly match `schemas/tier.schema.json::$defs.tier_block.allOf` +
# `docs/appendix/TIER_NAMING_SCHEMA_D.md`.
_TIER_BANDS: list[tuple[int, int, str, str, str]] = [
    (  0,   8, "I",    "Quark",         "\u22c5"),
    (  9,  16, "II",   "Atom",          "\u2299"),
    ( 17,  24, "III",  "Molecule",      "\u22ee\u22ee"),
    ( 25,  32, "IV",   "Stardust",      "\u2727"),
    ( 33,  40, "V",    "Nebula",        "\U0001f32b"),
    ( 41,  50, "VI",   "Protostar",     "\u2726"),
    ( 51,  60, "VII",  "Main Sequence", "\u2605"),
    ( 61,  68, "VIII", "Red Giant",     "\u25c9"),
    ( 69,  76, "IX",   "White Dwarf",   "\u26aa"),
    ( 77,  84, "X",    "Neutron Star",  "\u26ab"),
    ( 85,  92, "XI",   "Pulsar",        "\u25ce"),
    ( 93, 100, "XII",  "Singularity",   "\u25cf"),
]

# Map v0.7 verification_level → v0.8 identity_verification default
# (docs/LIFE_TIER_SPEC.md §6).
_VL_TO_IDENTITY: dict[str, str] = {
    "self_attested":         "self_attested",
    "third_party_verified":  "id_verified",
    "memorial_authorized":   "notarized",
}

BUILDER_VERSION = "0.2.0"
BUILDER_ID = f"tools/build_life_package.py@{BUILDER_VERSION}"


def _infer_asset_completeness(contents: list[dict]) -> str:
    """Heuristic — count capability-bearing top-level directories in the
    staged tree (pointers/ + assets/ + memory/ + knowledge/ + …). The
    builder only sees filenames, so this is intentionally coarse."""
    top_dirs: set[str] = set()
    for c in contents:
        parts = c["path"].split("/", 1)
        if len(parts) == 2:
            top_dirs.add(parts[0])
    cap_dirs = top_dirs & {"pointers", "assets", "memory", "knowledge", "voice", "avatar", "persona"}
    n = len(cap_dirs)
    if n <= 1:
        return "minimal"
    if n <= 3:
        return "partial"
    if n <= 5:
        return "standard"
    return "comprehensive"  # "archive_grade" is issuer-declared only


def _compute_tier(
    contents: list[dict],
    *,
    verification_level: str,
    computed_at: str,
    overrides: dict[str, str] | None = None,
) -> dict:
    """Deterministically compute the v0.8 tier block from package
    metadata. `overrides` lets the CLI lift specific dimensions above
    the conservative defaults (e.g. `--tier-detail-level high_fidelity`
    for a studio-recorded package). Score is rounded half-to-even per
    Python's `round`; the schema's ±0 tolerance is the authoritative
    check."""
    overrides = overrides or {}

    dims: dict[str, str] = {
        "identity_verification": _VL_TO_IDENTITY[verification_level],
        "asset_completeness":    _infer_asset_completeness(contents),
        # Consent + audit + jurisdiction default conservatively; issuers
        # lift them via CLI flags once the corresponding package
        # artefacts actually exist.
        "consent_completeness":  "text_only",
        "detail_level":          "medium",
        "audit_chain_strength":  "linked",
        "jurisdiction_clarity":  "unspecified",
    }
    for k, v in overrides.items():
        if k not in _TIER_ENUMS:
            raise SystemExit(f"unknown tier dimension: {k}")
        if v not in _TIER_ENUMS[k]:
            raise SystemExit(f"invalid level '{v}' for tier dimension {k}")
        dims[k] = v

    total_w = sum(_TIER_WEIGHTS.values())
    acc = 0.0
    for dim, level in dims.items():
        idx = _TIER_ENUMS[dim].index(level)
        max_idx = len(_TIER_ENUMS[dim]) - 1
        acc += (idx / max_idx) * _TIER_WEIGHTS[dim]
    score = max(0, min(100, round(acc * 100 / total_w)))

    for low, high, level, name, glyph in _TIER_BANDS:
        if low <= score <= high:
            return {
                "score": score,
                "level": level,
                "name": name,
                "glyph": glyph,
                "dimensions": dims,
                "computed_at": computed_at,
                "computed_by": BUILDER_ID,
            }
    raise SystemExit(f"tier banding failed for score {score}")  # unreachable


def _sha256_of(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_manifest(record_dir: Path) -> dict:
    p = record_dir / "manifest.json"
    if not p.exists():
        raise SystemExit(f"manifest.json not found under {record_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def _read_last_event(events_path: Path) -> dict | None:
    if not events_path.exists():
        return None
    last = None
    with events_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    return json.loads(last) if last else None


def _append_package_emitted_event(
    record_dir: Path,
    record_id: str,
    package_id: str,
    issuer_role: str,
    issuer_identifier: str,
    deterministic: bool,
    timestamp: str,
) -> tuple[Path, int]:
    """Append a `package_emitted` event to the source record's
    audit/events.jsonl. Returns (events_path, line_number_of_new_event)
    where line_number is 1-based.
    """
    events_path = record_dir / "audit" / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    last = _read_last_event(events_path)
    prev_hash = last["hash"] if last else None
    if last and "timestamp" in last and timestamp < last["timestamp"]:
        raise SystemExit(
            "package_emitted timestamp must be >= previous audit event timestamp; "
            "events.jsonl is append-only"
        )

    payload = {
        "event_id": _DET_EVENT_ID if deterministic else _new_ulid(),
        "event_type": "package_emitted",
        "record_id": record_id,
        "actor_role": "system",
        "actor_id": None,
        "timestamp": timestamp,
        "reason": f"Emitted .life package {package_id} per docs/LIFE_FILE_STANDARD.md",
        "evidence_ref": "life-package.json",
        "prev_hash": prev_hash,
        "metadata": {
            "package_id": package_id,
            "issuer_role": issuer_role,
            "issuer_identifier": issuer_identifier,
        },
    }
    payload["hash"] = _sha256_of(
        _canonical_dump({k: v for k, v in payload.items() if k != "hash"})
    )

    line = _canonical_dump(payload)
    with events_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    line_number = sum(
        1 for _ in events_path.open("r", encoding="utf-8") if _.strip()
    )
    return events_path, line_number


def _walk_pkg_files(staging_dir: Path) -> list[Path]:
    """All regular files under staging_dir, sorted by relative posix path,
    excluding life-package.json itself (which is the manifest of the
    manifests and is not listed in `contents[]`)."""
    files: list[Path] = []
    for p in staging_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(staging_dir).as_posix()
        if rel == "life-package.json":
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(staging_dir).as_posix())
    return files


def _validate_descriptor(descriptor: dict) -> None:
    if jsonschema is None:
        return
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(descriptor)


def _zip_deterministic(staging_dir: Path, out_path: Path) -> None:
    """Write a zip with sorted member order and a fixed mtime so that
    a deterministic build produces a byte-identical zip."""
    fixed_dt = (1980, 1, 1, 0, 0, 0)  # zip epoch
    files = _walk_pkg_files(staging_dir)
    pkg_json = staging_dir / "life-package.json"
    members = [pkg_json] + files
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for m in members:
            rel = m.relative_to(staging_dir).as_posix()
            zi = zipfile.ZipInfo(filename=rel, date_time=fixed_dt)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, m.read_bytes())


def build(args: argparse.Namespace) -> int:
    deterministic = _is_deterministic(args.deterministic)
    record_dir = Path(args.record).resolve()
    if not record_dir.is_dir():
        raise SystemExit(f"--record must be a directory: {record_dir}")
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "encrypted":
        # life-format v0.1 schema allows encrypted mode but the v0.1
        # reference builder explicitly does not implement encryption.
        # See docs/LIFE_FILE_STANDARD.md §3 + tracking issue.
        raise SystemExit(
            "encrypted-mode packaging is not implemented in this v0.1 reference "
            "builder; the schema declares it but real encryption requires KMS "
            "plumbing deferred to a future PR. Use --mode pointer."
        )

    manifest = _load_manifest(record_dir)
    record_id = manifest["record_id"]

    package_id = _DET_PACKAGE_ID if deterministic else _new_ulid()
    created_at = _DET_CREATED_AT if deterministic else _utc_now_iso()
    expires_at = (
        _DET_EXPIRES_AT
        if deterministic
        else (
            _dt.datetime.now(_dt.timezone.utc)
            + _dt.timedelta(days=args.lifetime_days)
        ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )

    # Step 1: append package_emitted event to SOURCE record.
    audit_timestamp = created_at
    events_path, line_number = _append_package_emitted_event(
        record_dir=record_dir,
        record_id=record_id,
        package_id=package_id,
        issuer_role=args.issuer_role,
        issuer_identifier=args.issuer_identifier,
        deterministic=deterministic,
        timestamp=audit_timestamp,
    )

    # Step 2: stage a copy of the source record subset.
    staging_dir = out_dir / f".staging-{package_id}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    # Files / dirs we copy verbatim into the .life. life-package.json
    # is written last and listed separately. encrypted/ is intentionally
    # not handled here (encrypted mode disabled in v0.1 builder).
    for entry in [
        "manifest.json",
        "consent",
        "policy",
        "audit",
        "derived",
        "pointers",
    ]:
        src = record_dir / entry
        if not src.exists():
            continue
        dst = staging_dir / entry
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)

    # Step 3: compute contents inventory of every staged file except
    # life-package.json (which we have not yet written).
    contents: list[dict] = []
    for p in _walk_pkg_files(staging_dir):
        rel = p.relative_to(staging_dir).as_posix()
        sha, size = _sha256_file(p)
        contents.append({"path": rel, "sha256": sha, "size": size})

    # Step 4: build life-package.json.
    tier_overrides: dict[str, str] = {}
    for dim in _TIER_ENUMS:
        val = getattr(args, f"tier_{dim}", None)
        if val is not None:
            tier_overrides[dim] = val

    descriptor = {
        "schema_version": "0.1.0",
        "package_id": package_id,
        "mode": "pointer",
        "record_id": record_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "issued_by": {
            "role": args.issuer_role,
            "identifier": args.issuer_identifier,
            "signature_ref": args.signature_ref,
        },
        "consent_evidence_ref": args.consent_evidence_ref,
        "verification_level": args.verification_level,
        "withdrawal_endpoint": args.withdrawal_endpoint,
        "runtime_compatibility": args.runtime_compatibility,
        "ai_disclosure": args.ai_disclosure,
        "forbidden_uses": args.forbidden_uses,
        "audit_event_ref": f"audit/events.jsonl#L{line_number}",
        "contents": contents,
    }
    if not args.no_tier:
        descriptor["tier"] = _compute_tier(
            contents,
            verification_level=args.verification_level,
            computed_at=created_at,
            overrides=tier_overrides,
        )
    _validate_descriptor(descriptor)

    pkg_json_path = staging_dir / "life-package.json"
    pkg_json_path.write_text(
        json.dumps(descriptor, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Step 5: zip into <out_dir>/<package_id>.life.
    out_path = out_dir / f"{package_id}.life"
    if out_path.exists():
        out_path.unlink()
    _zip_deterministic(staging_dir, out_path)

    # Step 6: cleanup staging.
    if not args.keep_staging:
        shutil.rmtree(staging_dir)

    print(
        f"built {out_path.relative_to(out_dir.parent)} "
        f"(package_id={package_id}, mode=pointer, "
        f"contents={len(contents)} entries, "
        f"audit_event_ref=audit/events.jsonl#L{line_number})"
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Build a .life archive from a DLRS source record (life-format v0.1.0)"
    )
    p.add_argument(
        "--record",
        required=True,
        help="Path to the source DLRS record directory (containing manifest.json)",
    )
    p.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the .life zip will be written",
    )
    p.add_argument(
        "--mode",
        choices=["pointer", "encrypted"],
        default="pointer",
        help="Distribution mode (v0.1 builder only supports 'pointer')",
    )
    p.add_argument(
        "--issuer-role",
        choices=["self", "authorized_representative", "memorial_executor"],
        default="self",
    )
    p.add_argument("--issuer-identifier", default="example-self")
    p.add_argument(
        "--signature-ref",
        default="consent/consent.md",
        help="Path inside the .life or external URI pointing to the issuer's signature artefact (opaque in v0.1)",
    )
    p.add_argument(
        "--consent-evidence-ref",
        default="consent/consent.md",
        help="Path inside the .life or external URI pointing to the consent document",
    )
    p.add_argument(
        "--verification-level",
        choices=["self_attested", "third_party_verified", "memorial_authorized"],
        default="self_attested",
    )
    p.add_argument(
        "--withdrawal-endpoint",
        required=True,
        help="URI runtimes MUST poll at session start and >=24h",
    )
    p.add_argument(
        "--runtime-compatibility",
        nargs="+",
        default=["dlrs-runtime-v0"],
        help="Runtime interface tokens this package declares",
    )
    p.add_argument(
        "--ai-disclosure",
        choices=["visible_label_required", "watermark_required", "metadata_only_with_consent"],
        default="visible_label_required",
    )
    p.add_argument(
        "--forbidden-uses",
        nargs="*",
        default=["impersonation_for_fraud", "political_endorsement", "explicit_content"],
        help="forbidden_uses[] list to embed into life-package.json",
    )
    p.add_argument(
        "--lifetime-days",
        type=int,
        default=365,
        help="Days from now until expires_at (ignored in deterministic mode)",
    )
    p.add_argument(
        "--deterministic",
        action="store_true",
        help="Pin package_id, timestamps, and audit event_id for byte-stable builds (or set DLRS_LIFE_DETERMINISTIC=1)",
    )
    p.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep the .staging-<package_id>/ directory after build (debugging)",
    )
    # v0.8 tier overrides — any dimension left unset is filled by
    # _compute_tier with the conservative default described in its
    # docstring.
    for dim, levels in _TIER_ENUMS.items():
        p.add_argument(
            f"--tier-{dim.replace('_', '-')}",
            dest=f"tier_{dim}",
            choices=levels,
            default=None,
            help=f"Override the {dim} tier dimension (default: auto)",
        )
    p.add_argument(
        "--no-tier",
        action="store_true",
        help="Omit the v0.8 tier block (v0.7 back-compat output)",
    )
    args = p.parse_args()
    return build(args)


if __name__ == "__main__":
    raise SystemExit(main())
