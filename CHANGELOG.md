# Changelog

All notable changes to the DLRS project will be documented in this file.

## v0.4 Draft (2026-04-26)

**Status**: RFC. Tightens the v0.3 schemas, makes AI disclosure machine-checked
for any public record, formalises the audit event log, and ships a static HTML
public registry. No breaking changes to v0.3 manifests beyond the new
conditional requirement on `public_disclosure` for `visibility = public_*`.

### Added

- `tools/batch_validate.py` — orchestrator that runs every validator
  (`check_sensitive_files`, `lint_schemas`, `validate_repo`, `validate_examples`,
  `validate_media`, `test_registry`, `build_registry`) and writes a single
  machine-readable report to `reports/validate_<utc-ts>.json`.
- `tools/emit_audit_event.py` — append-only writer for `audit/events.jsonl`,
  including a SHA-256 hash chain (`prev_hash` / `hash`) and refusal to rewrite
  existing `event_id`s.
- `docs/COMPLIANCE_CHECKLIST.md` — PIPL / GDPR / EU AI Act / 中国深度合成办法
  self-check, mapping each clause to a manifest field and a validator.
- `docs/LFS_GUIDE.md` — when to use Git LFS vs object-storage pointers, and a
  recipe for migrating an accidentally committed binary.
- Static HTML public registry: `tools/build_registry.py` now also writes
  `registry/index.html` (zero JS, inline CSS) alongside the existing JSONL/CSV.
- Examples: `examples/minor-protected/` and `examples/estate-conflict-frozen/`
  encode the two negative cases that registry generation must exclude.
- `tools/test_registry.py` adds two corresponding cases (now 14 total).

### Changed

- `schemas/manifest.schema.json`: added `public_disclosure` (with
  `ai_disclosure`, `label_text_required`, `label_locales[]`,
  `watermark_methods[]`, `c2pa_claim_generator`, `impersonation_disclaimer`).
  An `if/then` clause makes `public_disclosure` mandatory whenever
  `visibility ∈ {public_indexed, public_unlisted}`. Added optional
  `audit.events_log_ref`.
- `schemas/audit-event.schema.json`: tightened `event_type` to the eight
  canonical lifecycle events plus `custom`, restricted `actor_role` to a
  closed enum, added `evidence_ref`, `prev_hash`, `metadata`, and a
  hash-format pattern for `hash`. `additionalProperties` is now `false`.
- `.gitattributes`: added a comprehensive LFS routing list (audio, video,
  raw images, 3D / avatar formats, model weights, archives) plus
  `text eol=lf` normalisation for source files.
- `.github/workflows/validate.yml`: now also runs `batch_validate.py`,
  uploads `reports/` and `registry/index.html` as artefacts, and adds a
  separate non-blocking docs job (markdownlint + lychee linkcheck).
- `tools/build_registry.py`: emits HTML in addition to JSONL + CSV.
- `docs/GAP_ANALYSIS.md` and `docs/IMPLEMENTATION_STATUS.md` rewritten to
  reflect the post-v0.3 + v0.4 reality (overall completion ~78%).

### Closes

#17, #18, #19, #20, #21, #22, #23, #24, #25, #26.

---

## v0.3 Draft (2026-04-26)

**Status**: RFC (Request for Comments) stage — minimum viable repository goals.

### Added
- `docs/COLLECTION_STANDARD.md` — minimum media collection standard (audio,
  video, image, text, 3D) with hard rules and validation checklist.
- `docs/HIGH_FIDELITY_GUIDE.md` — aspirational high-fidelity collection
  guide and quality rubric.
- `docs/OBJECT_STORAGE_POINTERS.md` — formal pointer specification covering
  `s3://`, `oss://`, `cos://`, `minio://`, `obj://`, `repo://` schemes with
  required and forbidden fields.
- `tools/validate_media.py` — pointer media-metadata validator that enforces
  the minimum-collection thresholds (and optionally cross-checks local
  samples via `ffprobe`).
- `tools/lint_schemas.py` — Draft 2020-12 schema linter.
- `tools/validate_examples.py` — validates every `examples/*` archive.
- `tools/test_registry.py` — 12 unit tests for the public-registry
  inclusion / exclusion / data-integrity rules.
- `tools/upload_to_storage.py` — reference uploader for S3/OSS/COS/MinIO
  that emits a DLRS-conformant pointer file.
- `tools/estimate_costs.py` — monthly storage + egress cost projection.
- `.github/workflows/validate.yml` — restored CI pipeline (lint schemas,
  validate manifests, validate media metadata, run registry tests, build
  registry).
- `.github/ISSUE_TEMPLATE/takedown-request.yml`,
  `consent-withdrawal.yml`, `impersonation-dispute.yml` — privacy-aware
  GitHub Issue Forms with explicit warnings against attaching sensitive
  material publicly.

### Changed
- `schemas/pointer.schema.json` — added `artifact_type`,
  `media_metadata`, `encryption`, `retention_days`,
  `withdrawal_supported`, `consent_ref`, `review_status`, `provenance`;
  enforced `storage_uri` scheme allow-list and `checksum` format; forbade
  fields that would leak credentials or public download URLs.
- `schemas/consent.schema.json` — required `consent_version`,
  `captured_at`, `withdrawal_endpoint`, `allowed_scopes`; added
  `expires_at`, `signer`, scope enumeration.
- `schemas/public-profile.schema.json` — descriptions and an enum for
  `allowed_public_interactions` (preserving legacy values for
  backwards compatibility).
- `schemas/manifest.schema.json` — `schema_version` now accepts
  `0.2.x` and `0.3.x`; added descriptions and examples to top-level
  fields; relaxed `record_id` length to ≥ 4 to match existing examples.
- `.github/PULL_REQUEST_TEMPLATE/human-record.md` — full rewrite with
  consent / sensitive-materials / public-registry / withdrawal /
  reviewer-notes checklists.
- Replaced placeholder URLs and emails (`your-org/dlrs-hub`,
  `*@example.org`) with the canonical
  `Digital-Life-Repository-Standard/DLRS` repo, GitHub Discussions, and
  GitHub Security Advisories. Example/template manifest data was left
  intentionally fictional per issue #7's scope.

### Deprecated
- Schema `$id` URLs starting with `https://example.org/dlrs/` — replaced by
  `https://dlrs.standard/schemas/`. Existing manifests continue to validate.

### Notes
- Closes issues #6, #7, #8, #9, #10, #11, #12, #13, #14, #15.
- Still draft / RFC. v0.4 will add full GitHub Actions CI/CD coverage,
  Git LFS configuration, batch validation reports, and a minimal Web UI.

---

## v0.2 Draft (2026-04-26)

**Status**: RFC (Request for Comments) stage

### Added
- Complete repository structure (`humans/`, `registry/`, `policies/`, `operations/`)
- JSON schemas for manifest, consent, pointer, and public profile
- Consent and withdrawal model
- Privacy boundary definitions (S0-S4 sensitivity levels)
- Governance rules and review processes
- Validation and indexing tools
- Example archives (4 scenarios)
- Bilingual documentation (Chinese/English)
- Community documentation:
  - RFC: DLRS v0.2
  - Consent model feedback guide
  - Good first issues for contributors
  - Community promotion guide
- Legal disclaimers and ethical guidelines

### Changed
- Project positioning: Emphasize "open standard draft" rather than product
- README restructured for clarity and SEO
- Version badge changed to "v0.2 Draft" to reflect RFC stage

### Notes
- This is an early-stage draft for community feedback
- Not production-ready
- Seeking input on privacy model, consent framework, and ethical boundaries

---

## v0.1 (Initial public draft)

### Added
- Initial project structure
- Basic concepts and documentation
- Template files

### Notes
- First public release for initial feedback

