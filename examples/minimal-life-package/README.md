# minimal-life-package

> A reference walk-through of the **`.life` archive file format** (life-format v0.1.0). This example ships a small DLRS source record and a builder script that packages a consented subset of it into a portable, signed-by-reference, time-bounded `.life` zip.

**Spec**: [`docs/LIFE_FILE_STANDARD.md`](../../docs/LIFE_FILE_STANDARD.md) ·
**Schema**: [`schemas/life-package.schema.json`](../../schemas/life-package.schema.json) ·
**Runtime contract**: [`docs/LIFE_RUNTIME_STANDARD.md`](../../docs/LIFE_RUNTIME_STANDARD.md)

This example is **pointer-mode** only. Encrypted-mode packaging (AES-256-GCM
sealed blobs in `encrypted/`, KMS-distributed wrapping keys) is part of the
schema but is deferred — `tools/build_life_package.py` will refuse `--mode
encrypted` until the KMS plumbing lands in a follow-up.

## What gets packaged

The committed source record contains the bare minimum a v0.1 builder needs:

| Path | Purpose |
|---|---|
| `manifest.json` | DLRS source record (subset). Single subject, EU residency, voice sample held off-package via pointer. |
| `consent/consent.md` | Inline consent statement — referenced by `consent_evidence_ref`. |
| `policy/forbidden_uses.json` | The `forbidden_uses[]` list (mirrored verbatim into `life-package.json`). |
| `audit/events.jsonl` | Pre-existing audit chain (one `consent_verified` event). The builder appends a `package_emitted` event chained off that. |
| `derived/memory_atoms/sample.atoms.jsonl` | Three deterministic memory atoms used to demonstrate that derived assets travel inside the `.life` even in pointer mode (memory atoms are textual; no large biometric assets are bundled). |
| `pointers/voice_master.pointer.json` | Pointer file standing in for the upstream voice asset. The runtime resolves this only if it is authorised to fetch from the storage region declared in the pointer. |

## Build

```bash
./build_life.sh
```

Outputs `out/<package_id>.life` (zip). Each invocation:

1. Generates a fresh ULID for `package_id` (or pins it if `DLRS_LIFE_DETERMINISTIC=1`).
2. Appends a `package_emitted` event to the source record's `audit/events.jsonl`, chained off the prior event's `hash`.
3. Stages a copy of the source subset (manifest + consent + policy + audit + derived + pointers) under `out/.staging-<package_id>/`.
4. Computes the sha256 + size of every staged file.
5. Writes `life-package.json` with `audit_event_ref = "audit/events.jsonl#L<n>"` where `n` is the line number of the `package_emitted` event inside the *bundled* audit log.
6. Validates the descriptor against `schemas/life-package.schema.json`.
7. Zips the staged tree into `out/<package_id>.life` with deterministic member ordering and a fixed mtime (1980-01-01) so a deterministic build is byte-stable.

## Inspect the output

```bash
unzip -l out/*.life
# life-package.json
# audit/events.jsonl
# consent/consent.md
# derived/memory_atoms/sample.atoms.jsonl
# manifest.json
# pointers/voice_master.pointer.json
# policy/forbidden_uses.json
```

```bash
unzip -p out/*.life life-package.json | jq
```

`life-package.json` is the **single source of truth** for runtime mounting. It declares:

- `schema_version: "0.1.0"`
- `package_id` (ULID)
- `mode: "pointer"`
- `record_id: "dlrs_EXAMPLE_minimal_life"`
- `created_at` / `expires_at` (12-month default lifetime)
- `issued_by` (`role`, `identifier`, opaque `signature_ref` — v0.1 has no crypto signature scheme; deferred to life-format v0.2)
- `consent_evidence_ref: "consent/consent.md"`
- `verification_level: "self_attested"`
- `withdrawal_endpoint` (URI runtimes MUST poll at session start AND ≥ every 24h)
- `runtime_compatibility: ["dlrs-runtime-v0"]`
- `ai_disclosure: "visible_label_required"` (the absolute minimum)
- `forbidden_uses[]` (impersonation_for_fraud, political_endorsement, explicit_content, voice_clone_for_fraud, avatar_clone, memorial_reanimation_without_executor)
- `audit_event_ref: "audit/events.jsonl#L2"`
- `contents[]` — sha256 + size for every other file in the zip

## What a runtime does at load (per `LIFE_RUNTIME_STANDARD.md`)

1. Open the zip and parse `life-package.json` — refuse to mount if it doesn't validate against the schema.
2. Verify `created_at <= now < expires_at` — refuse if outside the window.
3. Recompute sha256 + size for every entry in `contents[]` against the corresponding zip member — refuse on any mismatch.
4. Walk `audit/events.jsonl` and verify the prev_hash chain is intact; refuse if any link is broken.
5. Resolve `consent_evidence_ref` — refuse if the consent document isn't reachable.
6. Poll `withdrawal_endpoint` once at session start; schedule re-polls at ≤ 24-hour intervals.
7. Mount the `.life` (pointer mode → asset references resolve to upstream storage; the runtime declines to mount any asset the storage region doesn't authorise).
8. Always tag every output as *AI digital life instance* (per `ai_disclosure`) — never claim equivalence to the human.
9. Refuse any prompt that maps to `forbidden_uses[]`.

## Re-runs grow the audit chain

Every invocation of `build_life.sh` appends one event to the source record's `audit/events.jsonl`. This is intentional — the audit log is append-only by design (v0.4 hash chain). To rebuild against a clean source state, restore `audit/events.jsonl` from git:

```bash
git checkout audit/events.jsonl
```

The test driver (`tools/test_minimal_life_package.py`) sidesteps this by copying the example to a tmp directory before each build, so the source committed under `examples/` always shows exactly one seed event.

## Testing

```bash
python tools/test_minimal_life_package.py
```

Verifies: (a) build exits 0, (b) `life-package.json` validates against the schema, (c) `contents[]` matches the zip exactly (sha256 + size for every member except `life-package.json`), (d) audit chain links are intact, (e) `audit_event_ref` resolves to the correct `package_emitted` line, (f) two consecutive deterministic builds produce byte-identical `life-package.json`.

This test is registered with `tools/batch_validate.py` (step `test_minimal_life_package`).
