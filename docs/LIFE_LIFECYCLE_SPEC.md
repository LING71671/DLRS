# `.life` Asset Lifecycle Specification (v0.8)

> **Status**: Normative draft, part of the `.life` Asset Architecture
> epic ([#106]). This file is the authoritative spec for how a `.life`
> package and the assets it ships **evolve, fork, expire, are
> withdrawn, are frozen, and are flipped to memorial**. Sub-issue
> [#102].
>
> This document is the per-topic normative spec for **Topic 2
> (Lifecycle)** of the v0.8 architecture discussion. Decisions made
> during that discussion are summarised in
> [`LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §3.
> When this spec and the architecture overview disagree, **this spec
> wins**.

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
[#102]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/102

Cross-references:

- Schema: [`schemas/lifecycle.schema.json`](../schemas/lifecycle.schema.json)
- Sanity tests: [`tools/test_lifecycle_schema.py`](../tools/test_lifecycle_schema.py)
- Architecture overview: [`docs/LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md)
- Genesis spec (asset provenance): [`docs/LIFE_GENESIS_SPEC.md`](LIFE_GENESIS_SPEC.md)
- File-format spec: [`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md)
- Runtime protocol: [`docs/LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md)

---

## 1. Purpose

A `.life` package is **not a static archive**. The subject's life
continues, the subject's mind changes, recordings get withdrawn,
methods get re-run, and at some point the subject dies. Without a
machine-checkable lifecycle layer, every consumer would have to
re-implement the same questions by hand:

1. **Is this package the latest version?** (Or is there a successor I
   should prefer?)
2. **Has it expired?** (`expires_at` reached)
3. **Has the subject withdrawn it?** (`withdrawal_endpoint` returned
   `withdrawn: true`)
4. **Is any input it depends on now withdrawn, contaminating derived
   assets?** (withdrawal cascade)
5. **Is the subject deceased and is this package now memorial-only?**
6. **How do I refuse safely?** (forks allowed; merges of unrelated
   subjects forbidden)

This spec answers all six. It defines four document shapes
(`package_lifecycle`, `asset_lifecycle`, `mutation_event`,
`cascade_index`), states the conformance language, and ties every
shape back to the five Topic-2 architecture decisions (D1–D5).

### Non-goals

- **Distribution / discovery.** How users find the latest version of a
  package over the network is the v0.10 distribution track.
- **UI for memorial / withdrawal.** The runtime protocol decides what
  to display; this spec only declares the machine-readable signals.
- **Automated re-build on input withdrawal.** This spec describes
  withdrawal cascade as marking assets `tainted`, not as automatically
  retraining replacements. Replacement is left to the package's
  operator.

---

## 2. Conformance language

The keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**,
**SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**,
and **OPTIONAL** are interpreted per RFC 2119.

This spec applies to:

- **Producers** of `.life` packages (operators, build tooling).
  Producers MUST emit lifecycle metadata for every package and every
  asset they ship.
- **Loaders / runtimes**. Loaders MUST evaluate the lifecycle signals
  before any user-facing interaction, and MUST refuse loads that the
  signals require to be refused (see §6).
- **Validators / archivers** (CI tooling, registries, third-party
  inspectors). They MUST be able to validate any lifecycle document
  against [`schemas/lifecycle.schema.json`](../schemas/lifecycle.schema.json)
  without context from the rest of the package.

---

## 3. Document layout

A v0.8 `.life` package adds **four** lifecycle document shapes on top
of the v0.7 layout:

```
life-package.json               # extended with package_lifecycle fields (§4)
genesis/
  <asset_id>.genesis.json       # extended with asset_lifecycle block  (§5)
lifecycle/
  <asset_id>.mutations.jsonl    # append-only mutation log             (§6)
  cascade_index.json            # source-input → derived-assets map    (§7)
```

Producers MUST place the per-asset mutation logs and the
`cascade_index.json` under a single top-level `lifecycle/` directory.
This keeps lifecycle data structurally separate from `audit/` (which
is the canonical event log) and from `genesis/` (which is the
provenance record).

The audit log under `audit/events.jsonl` remains the **canonical event
source**. Mutation logs are a denormalised per-asset view designed to
make the most common queries (withdrawal cascade, version timeline)
cheap to answer without scanning the full audit log. Producers MUST
emit one audit event for every mutation event; the mutation event
references the audit line via `audit_event_ref` and `audit_event_id`.

---

## 4. Package-level lifecycle (`package_lifecycle`)

The `package_lifecycle` shape adds five top-level fields to
`life-package.json`. Loaders MUST treat these fields as required for
v0.8-compliant packages.

### 4.1 Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `version` | semver | yes | Human-side identifier (decision **D1=D**). |
| `supersedes` | array | no (default `[]`) | At most ONE predecessor (decision **D2=C**, fork-yes / merge-no). |
| `lifecycle_state` | enum | yes | `active` / `superseded` / `expired` / `withdrawn` / `frozen` / `memorial`. |
| `frozen` | boolean | yes | MUST be `true` when `lifecycle_state ∈ {frozen, memorial}`. |
| `memorial_metadata` | object \| null | yes when `state == memorial` | See §4.3. |
| `recommended_re_consent_after` | datetime | no | Soft hint (decision **D5=C**); does NOT block. |

### 4.2 State semantics

| State | Subject alive? | Loader behaviour |
|---|---|---|
| `active` | yes | Normal load. |
| `superseded` | yes | Loader SHOULD prefer the newer version but MAY load this one for replay/audit. |
| `expired` | yes | Loader MUST refuse interactive use. |
| `withdrawn` | yes | Loader MUST refuse all use. |
| `frozen` | yes | Read-only loadable; no new writes. |
| `memorial` | no | Read-only loadable by default; MAY be extended only by an authorised executor (see §4.3). |

`expired` and `memorial` apply only at package level. Individual
assets cannot be in those states; the `asset_lifecycle_state` enum
(§5.1) is a strict subset.

### 4.3 Memorial metadata (decision **D4 = C + (a) + (c) + 7-day window**)

The `memorial_metadata` block is populated **only** when
`lifecycle_state == "memorial"` and MUST be `null` otherwise. The
schema enforces this via a top-level `if/then` rule.

| Field | Required | Notes |
|---|---|---|
| `triggered_at` | yes | Datetime the trigger was filed. |
| `trigger_kind` | yes | One of `executor`, `next_of_kin`, `court_order`. |
| `trigger_actor` | no | Identifier (email, DID, court reference) for audit. |
| `evidence_ref` | no | Path inside `consent/` or `audit/`; RECOMMENDED for `court_order`. |
| `dispute_window_ends_at` | no | `triggered_at + 7 days`. |
| `dispute_window_status` | no | `open` / `expired` / `cancelled_by_subject`. |
| `executor_can_extend` | no | True iff an authorised executor MAY sign new versions after the dispute window expires (decision sub-clause **(c)**). |

**Reverse-attestation dispute window.** Between `triggered_at` and
`triggered_at + 7 days`, the subject MAY contest the memorial trigger
by reverse-attesting via the v0.7 `withdrawal_endpoint`. If they do,
producers MUST set `dispute_window_status` to `cancelled_by_subject`
and reset `lifecycle_state` to `active`. Loaders MUST NOT treat the
package as memorial-confirmed until the dispute window has elapsed.

### 4.4 Forks allowed, merges forbidden (decision **D2 = C**)

The `supersedes` array MUST have **at most one** entry. The schema
enforces `maxItems: 1`. This makes one common attack class statically
unreachable: a malicious operator cannot stitch two unrelated
subjects' `.life` packages into a single descendant by listing both
predecessors.

Forking is fine: two new versions can both list the same predecessor.
A subject's package timeline is a tree, not a DAG.

### 4.5 Identity (decision **D1 = D**)

A package's identity is the **pair** `(version, sha256)`. The
human-facing `version` is the semver field above; the
machine-trusted `sha256` is the content hash of `life-package.json`
recorded in the package manifest (already required by v0.7). When
loaders compare two packages they MUST compare `sha256`; when humans
compare them they read `version`. The dual identity rules out the
"same version, different content" attack (the hash mismatch surfaces
the substitution).

---

## 5. Asset-level lifecycle (`asset_lifecycle`)

Each asset's `genesis/<asset_id>.genesis.json` (Topic 1) gains a
`lifecycle` block validating against `#/$defs/asset_lifecycle`.

### 5.1 Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `version` | semver | yes | Independent of the package's version. |
| `supersedes` | array | no | At most ONE predecessor `asset_id` (decision **D2=C**). |
| `created_at` | datetime | yes | First creation timestamp. |
| `last_mutation_at` | datetime | no | Datetime of the latest entry in the asset's mutation log. |
| `mutation_log_ref` | path | no | `lifecycle/<...>.mutations.jsonl`. REQUIRED when any non-creation mutation exists. |
| `expires_at` | datetime | no | Hard expiry for THIS asset (independent of the package's expiry). |
| `state` | enum | yes | `active` / `superseded` / `withdrawn` / `tainted` / `frozen`. |
| `tainted_reason` | string | yes when `state == tainted` | Free-form short explanation. |

### 5.2 The `tainted` state (decision **D3 = B**)

When a source input is withdrawn, derived assets MUST NOT be deleted
(deletion would break the audit chain) and MUST NOT be silently
re-served. Instead they are flipped to `state: tainted`. The schema
enforces that `tainted` requires `tainted_reason`.

Compliant runtimes MUST refuse to use `tainted` assets (the v0.7
`forbidden_uses` philosophy: refuse-by-default, no fallback).
Producers SHOULD write a follow-up `mutation_event` that points at
the `audit_event_ref` documenting the withdrawal.

`tainted` is asset-only. There is no package-level `tainted` state;
if every asset in a package is `tainted`, the package's
`lifecycle_state` SHOULD be flipped to `withdrawn` and a fresh build
issued from clean inputs.

### 5.3 Per-asset versioning

Asset versions move independently of package versions. A package
version bump need not bump every asset (a v2.3.0 package may still
ship the v1.0.0 voice clone). The dual identity rule (§4.5) applies
to assets via the manifest sha256 of each asset's underlying bytes.

---

## 6. Mutation log (`mutation_event`)

Each asset MAY have a mutation log at
`lifecycle/<asset_id>.mutations.jsonl`. The file is **append-only
JSONL**: every line MUST validate against
`#/$defs/mutation_event`. No line may be removed or rewritten.

### 6.1 Fields

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | Constant `dlrs-life-mutation/0.1`. |
| `ts` | yes | Datetime. |
| `asset_id` | yes | MUST match the asset whose log this is. |
| `action` | yes | One of `asset_created`, `input_added`, `input_withdrawn`, `asset_retrained`, `state_changed`, `superseded_by`. |
| `actor` | no | Identifier of the operator. |
| `from_state`, `to_state` | required iff `action == state_changed` | Use `asset_lifecycle_state` values. |
| `input_ref` | required iff `action ∈ {input_added, input_withdrawn}` | Reference to the source input. |
| `successor_asset_id` | required iff `action == superseded_by` | New asset's `asset_id`. |
| `audit_event_ref` | RECOMMENDED | Format `audit/<filename>#L<n>` (1-based; matches the repo convention). |
| `audit_event_id` | RECOMMENDED | Stable id of the matching audit event. |
| `reason` | no | Free-form short reason. |

### 6.2 Pairing with the audit log

For every mutation event, producers MUST emit a matching event in
`audit/events.jsonl`. The mutation event SHOULD reference that audit
line via `audit_event_ref` and `audit_event_id`. The audit log's
hash chain remains the authoritative tamper-evidence layer; the
mutation log is a denormalised view for fast per-asset queries.

### 6.3 Append-only conformance

Producers MUST treat each mutation log as append-only. Loaders MAY
verify append-only-ness by:

1. Re-reading the same file across runs and ensuring lines never
   disappear or change.
2. Cross-checking each mutation event against the corresponding audit
   event (the audit hash chain detects rewrites).

---

## 7. Cascade index (`cascade_index`)

`lifecycle/cascade_index.json` is a package-wide map from each
distinct source-input ref (recording, text, dataset, base model) to
**every asset that consumed it**, directly or transitively. This
makes the "which derived assets are tainted by withdrawing this
recording?" query O(1) instead of O(assets × inputs).

### 7.1 Schema

```json
{
  "schema_version": "dlrs-life-cascade-index/0.1",
  "generated_at": "2026-04-26T16:00:00Z",
  "entries": [
    {
      "source_input_ref": "raw/recording-2025-01-12.wav",
      "source_input_sha256": "<64 hex>",
      "derived_assets": ["voice-master-v1", "voice-style-warm-v1"]
    }
  ]
}
```

`derived_assets` is the **closure**: assets directly OR transitively
derived from the input. Producers SHOULD recompute the index whenever
a new asset is created or an input set changes.

### 7.2 Use by withdrawal cascade

A loader that observes `withdrawal_endpoint` returning
`source_input_withdrawn: <ref>` MUST:

1. Look up `<ref>` in `cascade_index.entries`.
2. For every `asset_id` in `derived_assets`, flip the asset's
   `state` to `tainted`, populate `tainted_reason`, and append a
   `mutation_event` with `action: input_withdrawn`.
3. Emit one audit event per cascade.

The cascade index does not change the audit log; it only pre-computes
the closure for the loader's convenience.

---

## 8. Decisions encoded in this spec

| # | Decision | Where it lands |
|---|---|---|
| **D1=D** | Dual identity: human semver + machine sha256 | `package_lifecycle.version`, manifest sha256, asset-level version |
| **D2=C** | Forks allowed, merges forbidden | `supersedes.maxItems: 1` on both `package_lifecycle` and `asset_lifecycle` |
| **D3=B** | Withdrawal cascade marks `tainted`, never deletes | `asset_lifecycle_state` enum + `tainted_reason` conditional |
| **D4=C+(a)+(c)+7d** | Memorial trigger from executor / next-of-kin / court; read-only loadable; executor MAY extend; 7-day reverse-attestation window | `memorial_metadata` block + top-level `if/then` rule on `lifecycle_state` |
| **D5=C** | `recommended_re_consent_after` is soft, never blocks | optional field on `package_lifecycle`; loader behaviour is "non-blocking banner" |

---

## 9. Schema realisation summary

`schemas/lifecycle.schema.json` exports four reusable shapes via
`$defs`:

- `package_lifecycle` — the fields added to `life-package.json`.
- `asset_lifecycle` — the block embedded in each `genesis/<id>.genesis.json`.
- `mutation_event` — one line of `lifecycle/<asset_id>.mutations.jsonl`.
- `cascade_index` — the file `lifecycle/cascade_index.json`.

Plus four enum / sub-shape primitives reused across the four
documents: `lifecycle_state`, `asset_lifecycle_state`,
`supersedes_entry`, `memorial_metadata`.

The schema does NOT directly validate any single file at the document
root — it only exports re-usable shapes referenced from other schemas
and from the lifecycle test suite. The companion update to
`schemas/life-package.schema.json` (so `life-package.json` validates
against `package_lifecycle` directly) is the v0.8 schema-integration
PR and is out of scope for this spec PR. Validators MAY apply the
fragments standalone in the meantime.

---

## 10. Sanity tests

`tools/test_lifecycle_schema.py` ships **39 cases** (4 happy-path +
35 negative) covering all four shapes:

- `package_lifecycle` (~10 cases): all six states, forks/merge limit,
  memorial conditional, frozen conditional, `recommended_re_consent_after`.
- `asset_lifecycle` (~10 cases): all five states, `tainted_reason`
  conditional, `mutation_log_ref` pattern, `expires_at` shape.
- `mutation_event` (~12 cases): every `action`, every conditional
  (`state_changed → from/to_state`, input_*\* → input_ref`,
  `superseded_by → successor_asset_id`), the 1-based
  `audit_event_ref` pattern, `additionalProperties: false`.
- `cascade_index` (~7 cases): `entries` non-empty, sha256 shape,
  `derived_assets` non-empty + unique, `additionalProperties: false`.

Run via:

```bash
python tools/test_lifecycle_schema.py
# or, as part of the full suite:
python tools/batch_validate.py
```

---

## 11. What is left out (deferred)

- **Per-asset distribution / discovery** (which copy of `voice-master-v1`
  is on which mirror) — v0.10 distribution track.
- **Automated retrain on input withdrawal** — left to operator
  tooling; the spec only requires the cascade flip.
- **Permission inheritance across forks** — out of scope; consent
  scopes are re-attested per package version (v0.7 already requires
  per-version signature).
- **Multi-subject merging** — explicitly forbidden by D2=C; not
  re-litigated here.

---

## Appendix A: Worked example

A package goes through the following lifecycle in a year:

1. **2026-04-01 v1.0.0 active.** `voice-master-v1` (asset) is
   created from `raw/recording-2025-12-15.wav`. Mutation log opens
   with `asset_created`.
2. **2026-06-12 v1.1.0 active.** A new recording is added; the asset
   is retrained. `voice-master-v1` gains an `asset_retrained` event
   with the new sha256. Package-level `version` bumps to `1.1.0`,
   `supersedes` lists the old `(1.0.0, sha256_old)`.
3. **2026-09-04 input withdrawn.** Subject withdraws
   `raw/recording-2025-12-15.wav`. Cascade runs: every asset in
   `cascade_index.entries[ref=…recording-2025-12-15.wav].derived_assets`
   is flipped to `state: tainted` with `tainted_reason: "source input
   recording-2025-12-15.wav was withdrawn 2026-09-04T08:00Z"`. A
   `mutation_event` of action `input_withdrawn` is appended.
4. **2026-09-15 v1.2.0 active.** Operator re-builds `voice-master`
   without the withdrawn recording; the new asset is `voice-master-v2`
   with `supersedes: [voice-master-v1]`. The package's `version`
   bumps to `1.2.0`.
5. **2027-02-20 memorial trigger.** Subject's executor files a
   memorial trigger (`trigger_kind: executor`,
   `triggered_at: 2027-02-20T12:00Z`). The dispute window opens.
6. **2027-02-27 dispute window expires.** No reverse-attestation
   filed. `dispute_window_status` flips to `expired`,
   `lifecycle_state` is now `memorial`, `frozen` is `true`, and
   `executor_can_extend` is set per the executor's signed declaration.

Every step above produces:

- one audit event in `audit/events.jsonl`,
- one or more mutation events in the affected
  `lifecycle/<asset_id>.mutations.jsonl`,
- (where applicable) an updated `cascade_index.json`,
- (where applicable) an updated `lifecycle_state` /
  `memorial_metadata` on `life-package.json`.

The spec gives every consumer enough information to reproduce that
timeline without consulting the operator.

---

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
[#102]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/102
