# LIFE Tier Specification (v0.8 / Topic 3)

**Status**: normative for v0.8 \
**Authoritative schema**: [`schemas/tier.schema.json`](../schemas/tier.schema.json) \
**Tier naming appendix**: [`docs/appendix/TIER_NAMING_SCHEMA_D.md`](appendix/TIER_NAMING_SCHEMA_D.md) \
**Architecture overview**: [`docs/LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §5 \
**Closes** sub-issue [#104](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/104) of epic [#106](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106).

This document is the per-topic normative specification for **Topic 3 — Tier System**
of the v0.8 Asset Architecture epic. It defines a six-dimensional credit-rating
system that replaces v0.7's single-dimension `verification_level` field.

## Conformance language

The keywords MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, REQUIRED, OPTIONAL are
to be interpreted as in [RFC 2119]. Schema-encodable rules are encoded in
`schemas/tier.schema.json`; cross-document rules and builder semantics are
described here.

## 1. Why a tier system

`.life` packages are not interchangeable. A studio-recorded, KYC-verified,
notarised consent document with a full audit chain is not the same artifact
as a self-attested text-only package, and runtimes / surfaces / downstream
verifiers need a machine-readable signal of that difference. v0.7 carried
this signal in a single field, `verification_level`, with three values:
`self_attested`, `third_party_verified`, `memorial_authorized`. This was
sufficient to express identity provenance but conflated four distinct
properties:

- the strength of the **issuer's identity**
- the **completeness** of the bundled assets
- the rigour of the bundled **consent**
- the audit / legal / fidelity **stack supporting the package**

Topic 3 unbundles these into six independent dimensions and derives a
single composite **score** (0–100) and **level** (I–XII) for use in UI,
discovery, and runtime decisions. The rating is fully public — credit
ratings cannot be hidden — and is auto-computed at build time so issuers
cannot inflate it.

## 2. Decisions encoded

| # | Decision | This spec realises it via |
|---|---|---|
| **D1=C** | Hybrid vocabulary on tier dimensions (closed enum at v0.8, no `x-` extension yet) | `enum` constraint on each of the six dimensions (`tier.schema.json::tier_dimensions`) |
| **D2=B(v0.8)** | Six dimensions adopted in full (no opt-out at v0.8) | All six fields are `required` in `tier_dimensions` |
| **D3=auto** | Tier MUST be auto-computed by the builder | `computed_by` pattern requires `<path>@<semver>`; the builder rejects hand-filled tier blocks pre-write (operational invariant; see §4) |
| **D4=public** | Tier is fully public, no hiding | The tier block lives in `life-package.json` (the open root descriptor); no separate "private tier" file |
| **D5=replace** | Tier replaces v0.7 `verification_level` (back-compat via mapping table) | `tier.dimensions.identity_verification` enum carries v0.7 semantics; mapping table in §6 |

## 3. The `tier` block

The tier block is a single JSON object. When integrated into
`life-package.schema.json` (a follow-on PR — out of scope here), it lives
under the top-level key `tier`. Standalone validation uses
`schemas/tier.schema.json`, which `$ref`s `#/$defs/tier_block`.

### 3.1 Field summary

| Field | Type | Required | Purpose |
|---|---|---|---|
| `score` | integer 0–100 | yes | Composite score, auto-computed |
| `level` | string I–XII | yes | Roman-numeral tier, deterministically derived from `score` |
| `name` | string | yes | Human-readable tier name from the active naming appendix |
| `glyph` | string | yes | Display glyph from the active naming appendix |
| `dimensions` | object | yes | Six independent dimension levels (see §3.2) |
| `computed_at` | datetime | yes | RFC 3339 / ISO 8601 UTC timestamp; equals `created_at` when integrated |
| `computed_by` | string | yes | Builder identifier `<path>@<semver>` (e.g. `tools/build_life_package.py@0.2.0`) |

`additionalProperties: false` at the block level. Unknown fields are
rejected — there is no `x-` extension namespace at the tier block level
(extensions, if any, attach to dimensions in a future spec revision).

### 3.2 The six dimensions

Each dimension is a closed enum (low → high). All six are required.

| Dimension | Levels (low → high) | Meaning |
|---|---|---|
| `identity_verification` | `unverified`, `self_attested`, `email_verified`, `id_verified`, `kyc_verified`, `notarized` | How firmly the issuer's identity is established |
| `asset_completeness` | `minimal`, `partial`, `standard`, `comprehensive`, `archive_grade` | How many capability classes have at least one bound asset |
| `consent_completeness` | `none`, `text_only`, `signed`, `notarized`, `multi_party_attested` | How well-founded the consent base is |
| `detail_level` | `low_fidelity`, `medium`, `high_fidelity`, `cinematic` | Per-asset fidelity averaged across the package |
| `audit_chain_strength` | `minimal`, `linked`, `signed_chain`, `notarized_chain` | Strength of the in-package audit chain |
| `jurisdiction_clarity` | `unspecified`, `declared`, `cross_validated`, `court_recognized` | How clearly the package declares its legal context |

Detailed level semantics live in the schema's `description` fields and are
the source of truth for builders.

## 4. Auto-computation (decision D3)

The builder MUST compute the tier at build time. Hand-filled tier blocks
are rejected:

- The schema's `computed_by` pattern (`^[A-Za-z0-9_./-]+@[A-Za-z0-9_.+-]+$`)
  rejects identifiers without a builder/version separator.
- The build tool (`tools/build_life_package.py`) computes `dimensions` from
  the package contents and writes the resulting block. A future PR wires
  this in fully; v0.8 ships the spec + schema + sanity tests, and the
  builder integration lands in the same PR that integrates the tier block
  into `life-package.schema.json`.
- An external party who hand-crafts a `tier` block can technically pass
  schema validation if they spoof a `computed_by` value, but the resulting
  block is verifiable: `score` MUST equal the deterministic function of
  `dimensions` (formula in §4.1), and `level` MUST satisfy the boundary
  binding (§4.2). Verifiers SHOULD recompute and reject mismatches.

### 4.1 Score formula

For dimension *i* with level index *kᵢ* (0-based, lowest = 0) and maximum
level index *Mᵢ*, contribution

```
contributionᵢ = (kᵢ / Mᵢ) × wᵢ
```

with default weights *wᵢ*:

| Dimension | Default weight |
|---|---|
| `identity_verification` | 2 |
| `consent_completeness` | 2 |
| `asset_completeness` | 1 |
| `detail_level` | 1 |
| `audit_chain_strength` | 1 |
| `jurisdiction_clarity` | 1 |

```
score = round( Σ contributionᵢ × 100 / Σ wᵢ )    # then clamp to [0, 100]
```

The weights are NORMATIVE for v0.8 — every conforming builder MUST use them
so two builders see the same package and produce the same score. Future
spec revisions MAY adjust weights, in which case the spec MUST also bump
the naming-appendix major version (so older `.life` packages keep their
historical tier).

### 4.2 Score → level boundaries

The boundaries are normative and enforced by the schema via `allOf` /
`if`-`then` rules:

| Level | Score range (inclusive) |
|---|---|
| I    |  0 –  8 |
| II   |  9 – 16 |
| III  | 17 – 24 |
| IV   | 25 – 32 |
| V    | 33 – 40 |
| VI   | 41 – 50 |
| VII  | 51 – 60 |
| VIII | 61 – 68 |
| IX   | 69 – 76 |
| X    | 77 – 84 |
| XI   | 85 – 92 |
| XII  | 93 – 100 |

Rationale lives in `docs/appendix/TIER_NAMING_SCHEMA_D.md`. A score of 67
with `level: "VII"` MUST fail validation (67 belongs to range VIII).

## 5. Naming appendix decoupling

`name` and `glyph` are sourced from a versioned appendix
(`docs/appendix/TIER_NAMING_SCHEMA_<X>.md`). For v0.8 the only appendix is
**Schema D — Cosmic Evolution** (Quark → Singularity). Future appendices
MAY ship without a spec major bump. Consumers MUST treat `level` (the
Roman numeral) as the canonical machine identifier and SHOULD NOT
machine-match on `name` or `glyph`.

A `.life` integrating Schema D MUST use the canonical names and glyphs
listed in the appendix table; UI consumers MAY substitute alternative
glyphs for accessibility, but the in-package values MUST be canonical
(reproducibility).

## 6. Migrating from v0.7 `verification_level`

v0.7's `verification_level` field carried three values. The mapping into
v0.8's `identity_verification` dimension is:

| v0.7 `verification_level` | v0.8 `tier.dimensions.identity_verification` |
|---|---|
| `self_attested` | `self_attested` |
| `third_party_verified` | `id_verified` (default) or `kyc_verified` (when issuer recorded a KYC chain) |
| `memorial_authorized` | `notarized` |

Notes:

- The mapping is a **default** for builders that don't have richer
  signals. Issuers SHOULD prefer the most specific level supported by
  their evidence.
- `memorial_authorized` carried *role-based* semantics in v0.7 (the
  issuer's `role == memorial_executor`). v0.8 keeps that role-based
  semantics in `life-package.schema.json` (untouched here) and uses
  `identity_verification: notarized` only as the tier-system mirror.
- Until the schema-integration PR lands, both v0.7 `verification_level`
  and v0.8 `tier` MAY coexist; integration will mark `verification_level`
  as deprecated in favour of `tier.dimensions.identity_verification`.

## 7. Cross-document interactions

| Other doc / schema | Interaction |
|---|---|
| `docs/LIFE_FILE_STANDARD.md` | The `.life` package descriptor (`life-package.json`) gains a `tier` block in a follow-on integration PR. No file format changes here. |
| `docs/LIFE_RUNTIME_STANDARD.md` | Topic 4 Assembly stage 2 (Resolve) MAY use `tier` to choose between candidate providers (lower-tier packages SHOULD prefer offline / lighter providers; higher-tier MAY prefer hosted higher-fidelity providers). Not normative — runtime is free to ignore tier. |
| `docs/LIFE_GENESIS_SPEC.md` | Genesis assets and tier are independent — a heavily-derived asset (low `reproducibility_level`) does not cap tier. |
| `docs/LIFE_LIFECYCLE_SPEC.md` | Tier MUST be recomputed on each new package version (`computed_at` advances with the lifecycle). |
| `docs/LIFE_BINDING_SPEC.md` | Binding and tier are orthogonal — tier rates the package itself; binding rates how runtimes should plug into it. A future spec MAY allow binding to assert a `tier_floor` (already implemented in `binding.schema.json::tier_floor`). |

## 8. Worked example

```json
{
  "tier": {
    "score": 54,
    "level": "VII",
    "name": "Main Sequence",
    "glyph": "★",
    "dimensions": {
      "identity_verification": "id_verified",
      "asset_completeness": "comprehensive",
      "consent_completeness": "signed",
      "detail_level": "high_fidelity",
      "audit_chain_strength": "linked",
      "jurisdiction_clarity": "declared"
    },
    "computed_at": "2026-04-26T14:00:00Z",
    "computed_by": "tools/build_life_package.py@0.2.0"
  }
}
```

Score derivation (level indices are 0-based; max-index is `len(enum) - 1`):

```
identity_verification = 3/5 × 2 = 1.20   (id_verified         at index 3 of 5)
consent_completeness  = 2/4 × 2 = 1.00   (signed              at index 2 of 4)
asset_completeness    = 3/4 × 1 = 0.75   (comprehensive       at index 3 of 4)
detail_level          = 2/3 × 1 = 0.67   (high_fidelity       at index 2 of 3)
audit_chain_strength  = 1/3 × 1 = 0.33   (linked              at index 1 of 3)
jurisdiction_clarity  = 1/3 × 1 = 0.33   (declared            at index 1 of 3)
sum                                = 4.28
sum_of_weights                     = 8
score = round(4.28 × 100 / 8)      = round(53.5) = 54   → tier VII (51–60)
```

The example block ships `score: 54`, exactly matching the formula's
output, and `level: "VII"` (range 51–60). Verifiers MAY recompute and
MUST reject any block where the recomputed score / level disagrees
with the persisted values.

## 9. What this spec does NOT cover

- **Builder integration into `life-package.schema.json`** — deferred to a
  follow-on integration PR that will fold the `tier` block into the
  package descriptor and migrate `verification_level` to deprecated.
- **`build_life_package.py` auto-compute implementation** — schema-only PR;
  the builder change lands together with the integration.
- **Runtime tier-aware provider selection** — non-normative; described
  briefly in the runtime spec via Topic 4.
- **Issuer signing of tier** — tier is auto-computed and inherits the
  package's signature; no separate tier signature.

## 10. Sanity tests

`tools/test_tier_schema.py` exercises **81 cases** (26 happy-path + 55
negative) covering:

- both boundaries of every score → level range (24 happy: 12 tiers × low + high)
- all-lowest and all-highest `tier_dimensions` (2 happy)
- score → level mismatch at every adjacent tier boundary (22 negative)
- missing required tier-block fields (7 negative)
- out-of-range / wrong-type score (4 negative)
- off-enum / wrong-type level (2 negative)
- empty / overlong name / glyph (3 negative)
- `computed_by` hand-rolled patterns (2 negative)
- `computed_at` type guard (1 negative)
- tier-block additional property (1 negative)
- missing each dimension (6 negative)
- per-dimension off-enum (6 negative)
- tier_dimensions additional property (1 negative)

The suite is wired into `tools/batch_validate.py`.

[RFC 2119]: https://www.rfc-editor.org/rfc/rfc2119
