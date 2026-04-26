# Changelog

All notable changes to the DLRS project will be documented in this file.

## v0.7-vision-shift Draft (in progress)

**Status**: Draft / WIP. Repositions DLRS's ULTIMATE from "Digital Life
Repository Standard 数字生命仓库标准" (Git-shaped repo structure standard)
to "**`.life` 可运行数字生命档案文件标准**" — a dual standard:

1. **`.life` archive file format** — the distribution unit, a packaged
   + signed subset of a DLRS v0.6 record.
2. **`.life` runtime protocol** — how compatible runtimes load + execute
   a `.life` to produce an *AI digital life instance*.

The DLRS Git repo continues to be the canonical authoring place for
v0.6 records. The `.life` file is the portable distribution unit,
runnable in any compatible runtime (chat / virtual world / 3D / …).

Tracked in epic
[#79](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/79)
under milestone
[`.life Archive + Runtime Standard (v0.7-vision-shift)`](https://github.com/Digital-Life-Repository-Standard/DLRS/milestone/5).
Sub-issues #80–#87, sub-PRs forthcoming.

This epic ships **specs + schema + example builder**. It does **not**
ship a working runtime — that is deferred to v0.8+.

### Added

- _(populated as sub-PRs land)_

### Changed

- _(populated as sub-PRs land)_

### Closes

- _(populated as sub-PRs land)_

### Hard rules (continued from v0.5/v0.6)

- One sub-issue = one PR. PR body MUST contain `Closes #N` on its own line.
- No force-push to master, no commit amends, no skipped hooks, no `git add .`.
- GitHub CI green is sufficient to merge. Devin Review is async non-blocking.
- `tools/batch_validate.py` MUST stay green at every merge.

### Ethical positioning (carried into every spec)

`.life` is **not** a resurrection technology, not a claim that the AI
instance equals the person, and not a consent-free post-mortem
reanimation tool. `.life` **is** a consented, revocable, auditable
digital representation — a signed, time-bounded license to operate an
AI instance under specified constraints, always identifiable as an
**AI digital life instance** rather than the underlying human.

---

## v0.6.0 (2026-04-26)

**Status**: Released. Builds on the v0.5 offline-first build pipelines with
memory atoms, a knowledge-graph extraction pipeline, a descriptor → audit
event bridge, and an opt-in hosted-API policy gate. Epic
[#52](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/52)
landed in 11 sub-PRs (#64–#75) under the v0.5 governance "one issue = one
PR, `Closes #N` on its own line" rule. Overall completion: ~88%.

Source of truth for these notes is the
[v0.6.0 GitHub Release](https://github.com/Digital-Life-Repository-Standard/DLRS/releases/tag/v0.6.0).

### Added

- `docs/PIPELINE_GUIDE.md` refreshed to v0.6: new §2.5 (`memory_atoms`),
  §2.6 (`knowledge_graph`), §3 (descriptor → audit bridge), §4
  (hosted-API opt-in policy gate). §6 author-a-pipeline checklist
  extended with the audit-bridge and hosted-API gate steps. §7 "what
  v0.6 deliberately is not" replaces the v0.5 equivalent. §8 references
  list now includes every v0.6 schema, module, and demo. (#62, this PR)
- `tools/test_pipelines.py` extended into the umbrella driver for the
  full DLRS pipeline test suite. Per-pipeline tests (asr / text /
  vectorization / moderation / memory_atoms / knowledge_graph) and the
  v0.6 cross-cutting tests (descriptor → audit bridge, hosted-API
  opt-in policy gate, memory-graph end-to-end demo) are now dispatched
  from a single entry point. The CI pipelines matrix invokes
  `python tools/test_pipelines.py` once on each of Python 3.11 and
  3.12; `tools/batch_validate.py` invokes it as the `pipelines` step
  while still listing the cross-cutting tests individually so a
  failure surfaces against a meaningful step name. (#61, this PR)
- `examples/memory-graph-demo/` — fully runnable v0.6 walkthrough that
  exercises `text` → `memory_atoms` → `knowledge_graph` end-to-end on a
  fictional 3-paragraph diary excerpt, prints the resulting
  hash-chained `audit/events.jsonl`, and demonstrates how each
  descriptor's `audit_event_ref` resolves to its line. Deterministic
  backends only (paragraph atomiser, regex extractor); zero hosted-API
  calls. `tools/test_memory_graph_demo.py` validates 8 expected
  artefacts, every descriptor, the 3-event hash chain, and back-fill
  consistency. Wired into `tools/batch_validate.py` (now 16 steps) and
  the pipelines CI matrix. (#60, this PR)
- `schemas/hosted-api-policy.schema.json` + `pipelines/_hosted_api.py` —
  per-record opt-in policy gate for hosted (online) AI APIs. Default DLRS
  remains offline-first; the only way to authorise a hosted-API code
  path is to commit a record-scoped `policy/hosted_api.json` document
  that declares `opt_in: true`, an `allowed_providers` whitelist, an
  `allowed_pipelines` whitelist, a `consent_evidence_ref`, and an
  `[issued_at, expires_at)` window. `pipelines._hosted_api.assert_allowed`
  refuses to authorise any combination outside the policy and raises
  `HostedApiNotAllowed`. Pipelines lazy-import the SDK *inside* the
  gated branch so the static `tools/validate_pipelines.py` ban on
  hosted-API imports continues to pass. (#59, this PR)
- `tools/test_hosted_api_policy.py` covers schema golden + 6 negative
  schema cases, default-deny when no policy file, `opt_in=false`
  short-circuit, provider/pipeline whitelists, `[issued_at, expires_at)`
  bounds, malformed-JSON refusal, and `list_allowed_providers`
  consistency. Wired into `tools/batch_validate.py` (now 15 steps)
  and the pipelines CI matrix. (#59, this PR)
- `pipelines/_audit_bridge.py` — descriptor → `audit/events.jsonl` bridge.
  Every pipeline (asr / text / vectorization / moderation / memory_atoms /
  knowledge_graph) now appends one `derived_asset_emitted` event per
  emitted descriptor and back-fills the descriptor's `audit_event_ref`
  with a stable `audit/events.jsonl#L<n>` reference. The bridge reuses
  the v0.4 emitter's hash-chain and schema validation, so audit
  integrity carries over unchanged. (#58, this PR)
- `--no-audit` flag on every pipeline CLI for fixture / dry-run
  invocations that must not produce an audit log entry. (#58, this PR)
- `tools/test_descriptor_audit_bridge.py` covering: event append, schema
  compliance, hash chain across two pipelines, descriptor back-fill,
  `--no-audit` skip, and silent-no-op when the record has no
  `manifest.json`. Wired into `tools/batch_validate.py` (14 steps) and
  the pipelines CI matrix. (#58, this PR)

### Changed

- `schemas/audit-event.schema.json::event_type.enum` extended with
  `derived_asset_emitted`. The eight v0.4 lifecycle events are unchanged;
  the new value is additive and `additionalProperties: false` on the
  enum still excludes any other custom strings. (#58, this PR)

### Closes

- #53 (housekeeping; PR #64)
- #54 (memory-atom schema; PR #65)
- #55 (entity-graph node + edge schemas; PR #66)
- #56 (memory_atoms pipeline; PR #67)
- #57 (knowledge_graph pipeline; PR #69)
- #70 (knowledge_graph regex newline fix; PR #71)
- #58 (descriptor → audit bridge; PR #72)
- #59 (hosted-API opt-in policy gate; PR #73)
- #60 (memory-graph demo; PR #74)
- #61 (pipeline tests + CI integration; PR #75)
- #62 (PIPELINE_GUIDE + GAP/STATUS/ROADMAP/CHANGELOG/README refresh; this PR)

---

## v0.5.1 (2026-04-26)

**Status**: Patch release on top of v0.5.0. Documentation-only — no schema,
code, behaviour, governance, or CI changes. Source of truth for these notes
is the [v0.5.1 GitHub Release](https://github.com/Digital-Life-Repository-Standard/DLRS/releases/tag/v0.5.1).

### Changed

- `redactions.json` field name corrected across CHANGELOG / `docs/PIPELINE_GUIDE.md`
  / `ROADMAP.md`: the actual field emitted by `pipelines/text/cleaning.py:90-96`
  is `kind` (e.g. `email`, `phone_cn`), not `rule_name`. Same correction
  applied to the moderation pipeline (`pipelines/moderation/policies.py:83-89`
  emits `rule`, not `rule_name`). Downstream consumers that keyed off the
  documented name would have failed to read the actual sidecar.
- Removed claims of "IBAN, IPv4/IPv6, generic passport" redaction from
  long-lived CN docs (`docs/IMPLEMENTATION_STATUS.md`, `ROADMAP.md`). The
  text pipeline implements exactly seven patterns: `url_with_credentials`,
  `email`, `id_cn`, `phone_cn`, `ipv4`, `credit_card_like`, `phone_generic`.
  No IBAN, no IPv6, no passport patterns ship in v0.5.

### Closes

- #50 (via PR #51).

---

## v0.5.0 (2026-04-26)

**Status**: RFC. Introduces the v0.5 offline-first build pipelines (ASR / text /
vectorization / moderation), a derived-asset provenance schema, and the
single-entrypoint pipeline CLI. No breaking changes to v0.4 manifests; the new
pipelines write everything under `derived/<name>/` so existing records are
untouched until a pipeline is explicitly run against them.

### Added

- `pipelines/` directory with the v0.5 pipeline contract:
  - `pipelines/__init__.py` — `PipelineSpec` registry + dispatcher.
  - `pipelines/_descriptor.py` — shared `DescriptorBuilder` that emits
    `<output>.descriptor.json` validated against
    `schemas/derived-asset.schema.json`.
  - `pipelines/asr/` — `dummy` (deterministic, no model) and `faster-whisper`
    (lazy-imported, opt-in) backends.
  - `pipelines/text/` — NFKC normalisation + conservative redaction
    (priority order: URLs with embedded credentials, emails, CN ID
    cards, CN mobile phones, IPv4 addresses, credit-card-like 13–19
    digit runs, generic phone numbers). Replacements use stable
    category placeholders (`<EMAIL>`, `<PHONE_CN>`, `<ID_CN>`, `<IPV4>`,
    `<CARD>`, `<PHONE>`, `<URL_WITH_CREDENTIALS>`). `redactions.json`
    sidecar carries `kind + start/end + replacement` only (`kind` is the
    rule name, e.g. `email`) and is auditable without re-leaking matched
    substrings.
  - `pipelines/vectorization/` — paragraph-aware chunking with absolute char
    offsets, `hash` (deterministic 64-D) and `sentence-transformers` backends,
    optional Qdrant push (`backend` and `model_id` stored as separate
    payload keys so downstream filters work without ambiguity).
  - `pipelines/moderation/` — deterministic regex/wordlist policy with
    severity-based outcome aggregation (`pass | flag | block`). Built-in
    v0.5 policy + `--policy-file` for JSON/YAML overrides. Flags carry
    rule + span only, **never** the matched substring.
- `tools/run_pipeline.py` — single CLI entrypoint (`python tools/run_pipeline.py
  <name> --record path/to/record …`) shared by every pipeline.
- `tools/validate_pipelines.py` — static guard: enforces the
  `derived/<spec.name>/` output-prefix invariant and refuses any module that
  imports a hosted-API client (`openai`, `anthropic`, `google.generativeai`,
  `cohere`, `aliyun_sdk_bailian`, …). This is what turns "offline-first" into
  machine-checked policy.
- `tools/test_pipelines.py` — umbrella test driver. Runs the four
  per-pipeline test scripts as subprocesses so an import failure in one
  pipeline cannot mask test results in another.
- `tools/test_asr_demo.py` — end-to-end test for `examples/asr-demo`.
- `schemas/derived-asset.schema.json` — provenance descriptor schema
  (`schema_version` / `derived_id` / `record_id` / top-level `pipeline` +
  `pipeline_version` / `actor_role` / `inputs.{source_pointers,inputs_hash}`
  / `output.{path,outputs_hash}` / optional `model.{id,version?,source?,
  online_api_used: false}` (required when pipeline is `asr` or
  `vectorization`) / optional `moderation_outcome`).
- `examples/asr-demo/` — self-contained fixture record. `run_demo.sh`
  regenerates a deterministic placeholder WAV (DLRS is pointer-first so
  audio is never committed) and walks all four pipelines end-to-end with
  no model download.
- `docs/PIPELINE_GUIDE.md` — companion to the example. Covers the contract,
  the descriptor, every pipeline's CLI, authoring guide, and what v0.5
  deliberately is not.
- `.github/workflows/validate.yml`: dedicated `pipelines` job parallel to
  `validate`, matrix over Python 3.11 and 3.12.

### Changed

- `tools/batch_validate.py`: collapsed the four per-pipeline tests into a
  single `pipelines` step delegating to `tools/test_pipelines.py`, then
  added `asr_demo` for the end-to-end fixture. Local report:
  `11/11 passed`.
- `docs/GAP_ANALYSIS.md` and `docs/IMPLEMENTATION_STATUS.md` rewritten to
  reflect v0.5 (overall completion ~83%).
- `ROADMAP.md`: v0.5 marked as released, with the `Closes #N`-per-PR
  governance rule appended to the v0.5 section so future major versions
  inherit it.

### Closes

#28 (epic), #29, #30, #31, #32, #33, #34, #35, #36, #37, #38.

---

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

