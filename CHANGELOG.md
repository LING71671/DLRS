# Changelog

All notable changes to the DLRS project will be documented in this file.

## v0.9 — Reference Runtime Implementation (in progress)

**Status**: Epic
[#119](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/119)
open. Goal: ship the reference runtime for `life-runtime v0.1.1`
(v0.7 §1–10 + v0.8 Part B 5-stage assembly), single `.life` only.
Multi-`.life`, `.world` and DLRS Extension Architecture remain v0.10+.

Sub-issues:
[#120](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/120)
scaffold,
[#121](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/121)
Stage 1 Verify,
[#122](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/122)
Stage 2 Resolve,
[#123](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/123)
Stage 3 Assemble,
[#124](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/124)
Stage 4 Run,
[#125](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/125)
Stage 5 Guard,
[#126](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/126)
echo Provider + e2e conformance harness + Quickstart docs.

### Added (sub-issue #120 — scaffold)

- `runtime/` Python package (`runtime/__init__.py` exporting `__version__
  = "0.9.0.dev0"` and `LIFE_RUNTIME_PROTOCOL_VERSION = "0.1.1"`) with
  empty sub-packages laid out for the 5 assembly stages: `verify/`,
  `resolve/`, `assemble/`, `run/`, `guard/`, plus `providers/` (built-in
  Provider implementations) and `audit/` (runtime-side hash-chain
  emitter). Each empty stage carries a one-line docstring naming the
  sub-issue that populates it.
- `runtime/cli/lifectl.py` — `lifectl` CLI entrypoint with three
  sub-commands. `lifectl version` prints `lifectl 0.9.0.dev0
  (life-runtime v0.1.1)` and exits 0. `lifectl info <pkg>` and
  `lifectl run <pkg>` parse their arguments but exit non-zero with a
  "not yet implemented in this sub-issue" message that points the
  reader at the right follow-up sub-issue (#121 / #121-#126).
- `pyproject.toml` at repo root — declares `dlrs-runtime` package
  (`name = "dlrs-runtime"`, `version = "0.9.0.dev0"`, `requires-python
  >= 3.10`, deps `jsonschema` + `pyyaml`) and exports the `lifectl`
  console script via `[project.scripts]`. Setuptools is told to
  package only `runtime*` so the existing `tools/` and `pipelines/`
  trees stay out of the wheel.
- `runtime/audit/emitter.py` — `RuntimeAuditEmitter` stub class that
  raises `NotImplementedError` referencing sub-issue #125 (the full
  v0.4 hash-chain emitter ships there).
- `runtime/README.md` — package-level overview pointing at the runtime
  spec and naming each sub-package's owning sub-issue.
- `tools/test_runtime_scaffold.py` — eight sanity-test cases covering
  package import, `Runtime` stub class, `lifectl version` output, the
  scaffold-only stub exits, `lifectl --help` listing all three
  sub-commands, the parseability of `pyproject.toml` (asserting the
  `lifectl` console-script entry), and that all eight `runtime/`
  sub-packages exist.
- `.github/workflows/validate.yml` — new `runtime-scaffold` CI job
  parallel to the existing `pipelines` job, matrix Python 3.11 + 3.12.
  Installs `dlrs-runtime` editable, runs the scaffold test driver, and
  asserts both that the `lifectl` console-script is on `PATH` (`lifectl
  version` succeeds) and that `lifectl info` / `lifectl run` exit
  non-zero in the scaffold-only build.

### Hard-rule invariants preserved

This sub-issue ships no execution code, so the v0.7 + v0.8 hard-rule
invariants (D1=C in-life sandbox / D2=B `bundled_in_life` Provider
refusal / D5=mixed hosted-API AND-gate / D6=fail-close Stage gating)
are upheld trivially: the scaffold cannot violate them because none of
the gates run yet. Sub-issues #121–#126 reinstate each invariant as
they implement the corresponding Stage.

## v0.8-asset-architecture (2026-04-26)

**Status**: Released. v0.8 closes the four asset-architecture gaps left
by v0.7-vision-shift: provenance (Genesis), evolution (Lifecycle),
consumption (Binding), and orchestration (Assembly), plus a
multi-dimensional tier system that replaces v0.7's single-axis
`verification_level`.

Tracked in epic
[#106](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106)
(closed). Sub-issues #100–#105 all merged; four post-merge review
follow-ups (#109, #112, #114, #116) merged alongside. Final integration
step (this release) folds the tier block into `life-package.schema.json`
and teaches `tools/build_life_package.py` to auto-compute it from
package contents, completing the v0.8 spec → builder loop.

### Added

- `docs/LIFE_ASSET_ARCHITECTURE.md` — authoritative human-readable
  record of the four-topic architecture discussion (Genesis /
  Lifecycle / Binding / Tier / Assembly). Single overview document
  capturing all final decisions, design rationale, cross-topic
  dependencies, the Schema D Cosmic Evolution naming registry
  (Quark → Singularity), the memorial dispute period (7-day
  reverse-attestation window), and a "rejected alternatives"
  appendix preserving institutional memory of options considered and
  declined. Entry point for sub-issues #101–#105 which deliver the
  per-topic normative specs and schemas. [#100]
- `docs/LIFE_GENESIS_SPEC.md` — per-topic normative spec for Topic 1
  (Asset Genesis). Defines `genesis/<asset_id>.genesis.json` and
  encodes the five Topic-1 decisions: base pretrained models as
  virtual assets (D1=C); hosted-API use declared but not blocking
  (D2=B); graded `reproducibility_level` enum (D3=C); fixed
  `consent_scope` enum (D4=A); separate `genesis/` directory (D5=B).
  [#101]
- `schemas/genesis.schema.json` — JSON Schema for the genesis file
  format (`dlrs-life-genesis/0.1`). Conditional rule:
  `compute.hosted_api_used: true` requires at least one entry in
  `compute.hosted_api_providers[]`. [#101]
- `tools/test_genesis_schema.py` — 36 sanity-test cases (4 happy-path
  + 32 negative) wired into `tools/batch_validate.py`. [#101]
- `docs/LIFE_LIFECYCLE_SPEC.md` — per-topic normative spec for Topic 2
  (Asset Lifecycle). Defines four document shapes
  (`package_lifecycle`, `asset_lifecycle`, `mutation_event`,
  `cascade_index`) and encodes the five Topic-2 decisions: dual
  human/machine identity (D1=D); forks allowed, merges forbidden
  (D2=C); withdrawal cascade marks derived assets `tainted` instead
  of deleting (D3=B); memorial trigger from executor / next-of-kin /
  court order with 7-day reverse-attestation window (D4=C+(a)+(c));
  `recommended_re_consent_after` is a soft hint that never blocks
  (D5=C). [#102]
- `schemas/lifecycle.schema.json` — JSON Schema exporting four
  reusable shapes via `$defs`. Conditional rules: `lifecycle_state ==
  "memorial"` requires `memorial_metadata` + `frozen: true`;
  `state == "tainted"` requires `tainted_reason`;
  `action == "state_changed"` requires `from_state` + `to_state`;
  `supersedes.maxItems: 1` enforces fork-yes / merge-no statically.
  Post-review tightening: `else` clause forces `memorial_metadata`
  to null on non-memorial states; `mutation_log_ref` pattern uses
  the same `..`-rejection lookahead as `life-package.schema.json`.
  [#102]
- `tools/test_lifecycle_schema.py` — 42 sanity-test cases (9
  happy-path + 33 negative) covering all four shapes, wired into
  `tools/batch_validate.py`. The 42 reflects the post-merge fixes
  applied in #110 (memorial `else` clause + `..` path-traversal
  rejection on `mutation_log_ref`) plus the asset_id pattern fix
  in #112. [#102]
- `docs/LIFE_BINDING_SPEC.md` — per-topic normative spec for Topic 3
  (Runtime Binding). Defines `binding/runtime_binding.json` and
  encodes the four locked Topic-3 decisions: hybrid capability
  vocabulary (D1=C, ~20 core enum + `x-` extension); issuer-self
  -decided engine strictness (D2=C, `strict: true | false`); hybrid
  hard-constraints keys with runtime fail-close on unknown keys
  (D4=C); AND-gate hosted-API decision (D5=A, issuer half only —
  user half is `policy/hosted_api.json` from v0.6). [#103]
- `schemas/binding.schema.json` — JSON Schema for the binding file
  format (`dlrs-life-binding/0.1`). `patternProperties` enforce both
  the capability-name hybrid vocabulary and the hard-constraints
  hybrid keyspace; `additionalProperties: false` makes unknown
  non-`x-` keys reject statically (decision D4=C fail-close at schema
  layer). [#103]
- `tools/test_binding_schema.py` — 63 sanity-test cases (11 happy-path
  + 52 negative) wired into `tools/batch_validate.py`. The 63 includes
  three negatives for `providers_whitelist_ref` path-traversal (added
  in #111 review fix-up) and eight more cases (6 negative + 2 happy)
  for path-traversal rejection on `surface.ui_hints.avatar_image_ref`
  and `surface.ui_hints.background_audio_ref`, applying the same
  cross-schema convention. [#103]
- `docs/LIFE_TIER_SPEC.md` — per-topic normative spec for Topic 3
  (Tier System). Defines a six-dimensional credit rating
  (`identity_verification`, `asset_completeness`,
  `consent_completeness`, `detail_level`, `audit_chain_strength`,
  `jurisdiction_clarity`), a normative weighted-score formula
  (consent + identity ×2, others ×1), 12 score → level boundaries
  (I–XII), and a back-compat mapping from v0.7 `verification_level`
  to `tier.dimensions.identity_verification`. [#104]
- `schemas/tier.schema.json` — JSON Schema for the v0.8 tier block
  (`dlrs-life-tier/0.1` shape via `$defs`). 12 `allOf` / `if`-`then`
  rules bind `score` ranges to Roman-numeral `level` values;
  `computed_by` pattern requires `<path>@<semver>` so hand-rolled
  tier blocks fail validation. Standalone for v0.8; integration into
  `life-package.schema.json` deferred to a follow-on PR. [#104]
- `docs/appendix/TIER_NAMING_SCHEMA_D.md` — versioned naming
  appendix listing the 12 Schema D tiers (Cosmic Evolution: Quark →
  Singularity), their canonical names, glyphs, score ranges, and
  cosmological reading. The appendix is decoupled from
  `LIFE_TIER_SPEC.md` so future naming schemes can ship without a
  spec major bump. [#104]
- `tools/test_tier_schema.py` — 81 sanity-test cases (26 happy-path
  + 55 negative) covering both ends of every score → level range,
  every score → level mismatch boundary, every required-field
  removal, every dimension off-enum, and the auto-computation guard
  on `computed_by`. Wired into `tools/batch_validate.py`. [#104]
- `docs/LIFE_RUNTIME_STANDARD.md` — appends Part B with normative
  v0.8 additions for Topic 4 (Runtime / Assembly): the five-stage
  assembly pipeline (Verify / Resolve / Assemble / Run / Guard),
  the Provider Registry concept, the abstract
  `LifeCapabilityProvider` interface, the three-tier sandbox class
  (`built_in` / `user_installed` / `bundled_in_life`), the
  hosted-API AND-gate, and the OS-package-manager bootstrap rule.
  Encodes Topic 4 decisions D1=C (graded sandbox), D2=B (no
  bundled providers in v0.8), D3=mixed (offline + hosted both
  first-class), D4=C (three-field surface — already in binding
  spec), D5=C (OS package manager bootstrap), and the new D6
  (fail-close stage gating). Adds four new audit event types:
  `capability_bound`, `assembly_aborted`, `withdrawal_poll` (reuse of
  the v0.7 event with a v0.8 field requirement), and
  `lifecycle_transition_observed`. Part A (the v0.7 eight-step
  load sequence) is unchanged. [#105]
- `schemas/life-package.schema.json` — v0.8 integration: adds optional
  top-level `tier` property referencing inlined `$defs.tier_block` +
  `$defs.tier_dimensions` (copied verbatim from
  `schemas/tier.schema.json` so offline validators do not need to
  resolve cross-file `$ref`). Marks `verification_level` as deprecated
  in description text (remains REQUIRED for v0.1 back-compat). 10 new
  sanity cases in `tools/test_life_package_schema.py` (64 total, up
  from 54): tier omitted (back-compat), tier present (consistent
  score/level), lowest / highest boundary, score↔level mismatch
  rejection, hand-rolled `computed_by` rejection, score out of range,
  off-enum dimension, missing required dimension, unknown tier field.
- `tools/build_life_package.py` v0.2 — auto-computes the `tier` block
  from the staged package: maps v0.7 `verification_level` to v0.8
  `identity_verification` per `docs/LIFE_TIER_SPEC.md` §6, infers
  `asset_completeness` from capability-bearing top-level directories,
  defaults the remaining four dimensions conservatively, applies
  weighted-average scoring (identity & consent ×2, others ×1), and
  bands the result into the 12 Schema D tiers. Adds six
  `--tier-<dim>` CLI overrides and a `--no-tier` escape hatch for
  emitting v0.7-shaped descriptors. `computed_by` is stamped with the
  mandatory `@<version>` separator so hand-rolled tier blocks fail
  schema validation.
- `docs/LIFE_FILE_STANDARD.md` — adds the `tier` row to the
  top-level descriptor table and marks `verification_level` as
  deprecated in v0.8, pointing at `docs/LIFE_TIER_SPEC.md` §6 for the
  migration mapping.

### Changed

- `docs/IMPLEMENTATION_STATUS.md` — bumped to doc version 6.0 with a
  new v0.8 increment summary; overall maturity adjusted from ~80% to
  ~82% (Asset Architecture + Tier + Assembly spec deltas).
- `docs/GAP_ANALYSIS.md` — baseline moved to post-#106; `.life`
  Archive Standard maturity 70% → 82%, `.life` Runtime Standard
  30% → 45%; overall 80% → 82%.
- `ROADMAP.md` — marks `life-format v0.1.0` and `life-runtime v0.1`
  as Delivered; adds `life-format v0.1.1` (Asset Architecture) and
  `life-runtime v0.1.1` (Assembly) rows as Delivered under
  v0.8-asset-architecture; reference runtime deferral moved from
  v0.8+ to v0.9+.

[#101]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/101
[#102]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/102
[#103]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/103
[#104]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/104
[#105]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105


## v0.7-vision-shift (2026-04-26)

**Status**: Released. Repositions DLRS's ULTIMATE from "Digital Life
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
All 8 sub-issues #80–#87 closed; PRs #88, #89, #91, #92, #93, #94,
#95, #97, #98 merged.

This epic ships **specs + schema + example builder**. It does **not**
ship a working runtime — that is deferred to v0.8+.

### Added

- `docs/LIFE_FILE_STANDARD.md` — authoritative `.life` archive
  file-format specification (life-format v0.1.0). Defines `.life` as a
  zip with mandatory directories (`manifest/`, `consent/`, `policy/`,
  `audit/`, `derived/`) plus optional (`pointers/`, `encrypted/`); two
  modes (`pointer` privacy-preserving and `encrypted` off-grid full pack);
  mandatory metadata fields (`mode`, `record_id`, `issued_by`,
  `consent_evidence_ref`, `verification_level`, `withdrawal_endpoint`,
  `runtime_compatibility`, `ai_disclosure`, `forbidden_uses`,
  `audit_event_ref`, `contents`, `expires_at`); ethical boundaries
  (`.life` is not resurrection, instance must always be identifiable
  as AI, must be revocable and auditable). PR #89 + post-merge fix
  PR #91 (eight-entries miscount). [#81 / #90]
- `docs/LIFE_RUNTIME_STANDARD.md` — authoritative runtime protocol
  spec (life-runtime v0.1). Defines the 8-step load sequence (verify
  schema → verify time window → verify integrity → verify audit chain
  → resolve consent → poll withdrawal endpoint → mount → expose
  identity / withdrawal / audit hooks); runtime obligations (visible
  AI disclosure, `forbidden_uses[]` refusal, ≥ 24h withdrawal poll,
  `expires_at` refusal-to-continue, no cross-`.life` memory mixing);
  termination triggers; prohibited behaviours; conformance clauses;
  ethical boundaries. PR #93. [#84]
- `schemas/life-package.schema.json` — contract for `life-package.json`
  inside every `.life`. Draft 2020-12; pointer/encrypted bi-conditional;
  memorial → executor bi-conditional; sha256 hex case-insensitive;
  `forbidden_uses[]` must include `fraud`, `political_impersonation`,
  `sexually_explicit_unconsented`; `expires_at > created_at`;
  `contents[]` paths reject `..` and absolute paths. 54/54 sanity test
  cases pass (`tools/test_life_package_schema.py`). PR #92 + post-merge
  fix PR #97 (sha256 hex case-insensitivity). [#82 / #96]
- `examples/minimal-life-package/` + `tools/build_life_package.py` —
  reference example record subset (manifest + consent + policy +
  audit seed + derived/memory_atoms + voice pointer) and
  pointer-mode-only builder implementing the §5 authoring workflow
  (stage → append `package_emitted` audit event → sha256 inventory
  → write `life-package.json` → schema-validate → deterministic zip).
  `--mode encrypted` is rejected with a guard message until KMS
  plumbing lands. End-to-end test driver
  (`tools/test_minimal_life_package.py`) verifies schema validation,
  `contents[]` matches zip members, audit chain integrity, and that
  two consecutive deterministic builds produce byte-identical
  `life-package.json`. Wired into `tools/batch_validate.py` as step
  `minimal_life_package` (now 18/18). PR #98. [#83]
- `audit-event.schema.json::event_type.enum` adds `package_emitted`
  (used by the `.life` builder when appending to the source record's
  `audit/events.jsonl`). Backward-compatible additive change; mirrors
  v0.6's `derived_asset_emitted` pattern. PR #98. [#83]
- README first-screen + README.en.md repositioning to make DLRS = `.life`
  dual standard the headline claim. "What is DLRS?" split into archive
  format / runtime protocol / supporting infrastructure; explicit
  "What is NOT" / "What IS" framing for `.life` instances (not real
  human resurrection; must be revocable, auditable, always identifiable
  as an AI instance). PR #94. [#85]
- `ROADMAP.md` introduces two independent semver tracks decoupled from
  the repo's v0.x.y: "Track A — `.life` Archive Standard"
  (life-format v0.1.0 / v0.2.0 / v0.3.0) and "Track B — `.life` Runtime
  Standard" (life-runtime v0.1 / v0.2 / v0.3). Repo v0.x.y continues
  to track tooling + examples + governance. PR #95. [#86]
- `docs/IMPLEMENTATION_STATUS.md` + `docs/GAP_ANALYSIS.md` refreshed to
  reflect the new `.life` dual-standard ULTIMATE: maturity table adds
  `.life Archive Standard` (70%) and `.life Runtime Standard` (30%,
  specs only); GAP_ANALYSIS §0 dedicated to the two new tracks; §13
  rewritten to call out the `.life` runtime / encrypted-mode / signing
  gaps. Overall completion adjusted from 88% to ~80% to reflect the
  expanded scope. PR (this PR). [#87]
- `CHANGELOG.md` v0.7-vision-shift entry promoted from Draft to release.

### Changed

- DLRS ULTIMATE positioning shifts from "Git-shaped repo standard" to
  "`.life` archive file format + runtime protocol dual standard".
  Existing v0.6 record structure remains the canonical authoring
  surface; `.life` is the portable distribution unit packaged from a
  consented subset of that record.
- `audit-event.schema.json::event_type.enum` extended additively
  (`package_emitted`); existing event types' semantics unchanged.
- README / ROADMAP framing language across the repo updated to make
  the `.life` dual-standard the headline claim.

### Closes

- #80 — housekeeping (PR #88)
- #81 — `docs/LIFE_FILE_STANDARD.md` (PR #89)
- #82 — `schemas/life-package.schema.json` + 54 sanity tests (PR #92)
- #83 — `examples/minimal-life-package/` + `tools/build_life_package.py`
  (PR #98)
- #84 — `docs/LIFE_RUNTIME_STANDARD.md` (PR #93)
- #85 — README first-screen `.life` repositioning (PR #94)
- #86 — `ROADMAP.md` `.life` Archive + Runtime Standard tracks (PR #95)
- #87 — `IMPLEMENTATION_STATUS` + `GAP_ANALYSIS` reflect new ULTIMATE
  (this PR)
- #90 — post-#89 LIFE_FILE_STANDARD eight-entries miscount fix (PR #91)
- #96 — post-#92 sha256 hex pattern case-insensitivity fix (PR #97)

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

