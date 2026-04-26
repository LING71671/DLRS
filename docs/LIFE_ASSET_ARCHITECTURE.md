# `.life` Asset Architecture (v0.8)

> Status: **Draft**, part of the `.life` Asset Architecture epic
> ([#106]). This document is the authoritative human-readable record of
> the four-topic architecture discussion that closed on 2026-04-26
> (Genesis / Lifecycle / Binding / Tier / Assembly), and is the entry
> point for all v0.8 spec PRs.
>
> Per-topic normative specs live in their own files (linked below).
> When this overview and a per-topic spec disagree, the per-topic spec
> wins.

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106

Cross-references:

- File format spec — [`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md)
- Runtime protocol spec — [`docs/LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md)
- Package schema — [`schemas/life-package.schema.json`](../schemas/life-package.schema.json)
- Genesis spec — `docs/LIFE_GENESIS_SPEC.md` ([#101], to be delivered)
- Lifecycle spec — `docs/LIFE_LIFECYCLE_SPEC.md` ([#102], to be delivered)
- Binding spec — `docs/LIFE_BINDING_SPEC.md` ([#103], to be delivered)
- Tier spec — `docs/LIFE_TIER_SPEC.md` ([#104], to be delivered)

[#101]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/101
[#102]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/102
[#103]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/103
[#104]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/104
[#105]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105

---

## 1. Why this document exists

`.life` v0.7 (epic [#79]) repositioned the project as the dual standard
ULTIMATE: an authorized **file format** plus an authorized **runtime
protocol**. v0.7 froze the package layout (`manifest/`, `consent/`,
`policy/`, `audit/`, `derived/`, `pointers/`, `encrypted/`) and the
8-step runtime load sequence. That is enough to *describe* a `.life`
package, but not enough to *trust* or *operate* one.

[#79]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/79

Four gaps remained:

1. **Provenance** — given an asset (a voice clone, a memory atom set,
   a knowledge graph), nobody could machine-check where it came from,
   what authorised it, what compute touched it, or whether a hosted
   API ever saw the inputs.
2. **Mutation** — assets evolve. v0.7 had no answer for version chains,
   withdrawal cascades from a single source recording into multiple
   derived assets, memorial freeze, or post-mortem extension.
3. **Consumption** — runtimes had no normative way to pick the right
   engine for an asset, declare permanently-forbidden behaviours,
   describe the required UI surface, or interact with the v0.6
   hosted-API gate.
4. **Orchestration** — runtimes had a load sequence but no model for
   how providers register, plug in, are sandboxed, fall back, and
   bootstrap on a fresh OS.

This epic (v0.8) closes those four gaps with four asset-layer specs
(Genesis / Lifecycle / Binding / Tier) and one runtime-side update
(5-stage assembly + Provider Registry). Each topic was discussed as a
draft + decision-points round in late April 2026. This document
records the final decisions, their rationale, and the alternatives
that were considered and rejected.

---

## 2. Topic 1 — Asset Genesis

### 2.1 Problem

Every asset in a `.life` must answer four questions: **what inputs**,
**what method**, **whose authorisation**, **where did the compute
happen**. Without those answers, downstream cannot do withdrawal
cascades, reproducibility audits, or hosted-API leak detection.

### 2.2 Solution

Every asset gets a sibling file `genesis/<asset_id>.genesis.json` with
five sub-blocks:

1. `method` — `name`, `version`, `config_ref`, `code_repo`, `code_commit`
2. `source_inputs[]` — `type`, `ref`, `sha256`, `consent_ref`, `consent_scope[]`
3. `compute` — `platform`, `operator`, `started_at`, `finished_at`, `hosted_api_used`, `hosted_api_providers[]`, `data_left_local`
4. `consent_scope_checked` — `verified`, `verifier`, `verifier_version`, `verified_at`, `scopes_used[]`
5. `audit_event_ref` + `audit_event_id`

Plus three top-level qualifiers:

- `base_model` — the pretrained model used as the starting point, listed as a virtual asset.
- `reproducibility_level` — `bit_identical | param_identical | not_reproducible`.
- `consent_scope` enum entries — drawn from a fixed v0.8 vocabulary.

### 2.3 Decisions

**D1 = C — Base pretrained models are virtual assets in `.life`.**
A voice clone is not really *one* asset; it is a fine-tune on top of a
base model. We list the base model (`name`, `license`, `sha256`,
`source_url`) as a virtual asset so the package is self-describing
and downstream can verify license compatibility. License disputes (e.g.
non-commercial CC-BY-NC for XTTS-v2) are resolved between users; the
spec only requires disclosure.

**D2 = B — `hosted_api_used = true` is declared but NOT fatal.**
Hosted-API use is a privacy event; loaders must know it happened and
who saw the data. But blocking hosted-API genesis would exclude almost
every realistic high-quality `.life`. Declare and let the loader
decide. The loader trust signal is preserved by the tier system (see
section 5).

**D3 = C — `reproducibility_level` is a graded enum.**
Strict bit-identical reproducibility is impossible for most ML
training (CUDA non-determinism, etc.). Rather than ban
non-reproducible assets, the spec lets them declare their level and
forces the loader to acknowledge it. `bit_identical` =
seed-+-pipeline-deterministic; `param_identical` = same training inputs
and method but parameters may differ across runs; `not_reproducible`
= retraining will not yield equivalent assets.

**D4 = A — `consent_scope` is a fixed enum.**
Free-text consent scopes would cause every issuer to invent its own
vocabulary. The spec ships ~15 enumerated scopes
(`voice_clone`, `memorial_voice`, `text_persona`, `image_avatar`,
`video_avatar`, `interactive_chat`, etc.) and grows the list with
spec versions. New scopes are additive; old packages stay valid.

**D5 = B — Genesis lives in a separate `genesis/` directory.**
Asset descriptors stay short (so runtimes can load fast); genesis
files carry the heavy provenance detail (so audit / withdrawal /
reproducibility work has a single place to look). The link between
descriptor and genesis is sha256-hashed, so tampering with one breaks
the chain.

### 2.4 What is left out

- We do **not** require deterministic builds across machines (most
  modern training cannot meet that bar).
- We do **not** validate `base_model.license` machine-readably (the
  set of acceptable licenses is loader policy, not spec).
- `consent_scope` does **not** model temporal restrictions
  ("voice_clone allowed from 2025 to 2030"); that lives in the
  consent evidence document.

---

## 3. Topic 2 — Asset Lifecycle

### 3.1 Problem

Assets are alive. The same person ships multiple versions, withdraws a
single source recording with cascading effects on derived voice and
memory, eventually dies, and may have a designated executor extend
the package on their behalf. Without lifecycle, a `.life` is a frozen
snapshot and the four signal classes — revocation, expiration, death,
drift — cannot propagate.

### 3.2 Solution

Two layers of lifecycle metadata:

**Package level** (in `life-package.json`):

```json
{
  "version": "2.3.0",
  "supersedes": [
    { "package_id": "...", "version": "...", "sha256": "..." }
  ],
  "lifecycle_state": "active | superseded | expired | withdrawn | frozen | memorial",
  "frozen": false,
  "memorial_metadata": null
}
```

**Asset level** (inside each `*.genesis.json`):

```json
"lifecycle": {
  "version": "1.3.0",
  "supersedes": ["voice-master-v0.9.0"],
  "created_at": "2025-02-03T16:00:00Z",
  "last_mutation_at": "2026-04-20T00:00:00Z",
  "mutation_log_ref": "lifecycle/voice-master-v1.mutations.jsonl",
  "expires_at": "2027-02-03T00:00:00Z",
  "state": "active | superseded | withdrawn | tainted | frozen"
}
```

A package-level `lifecycle/cascade_index.json` maps every source-input
ref to the list of derived assets that consumed it, so withdrawing a
single source ref propagates deterministically.

Mutation logs (`lifecycle/<asset_id>.mutations.jsonl`) are append-only
JSONL records of `asset_created`, `input_added`, `input_withdrawn`,
`asset_retrained`, etc.

### 3.3 Decisions

**D1 = D — Hybrid identity: semver for humans, content sha256 for
machines.**
Humans need to distinguish "minor patch" from "major retrain"
(semver). Machines must not be fooled by collisions (content hash).
The spec carries both; runtimes trust the hash; humans read the
semver.

**D2 = C — Supersedes can fork (one-to-many) but NOT merge
(many-to-one).**
Forking captures real scenarios — Alice ships one `.life` for public
chat and another containing medical memories for hospital use; both
descend from the same base. Merging would silently combine
permission sets; that is exactly the kind of attack the spec must
prevent. Each new version supersedes at most one predecessor; a
predecessor may be superseded by multiple descendants.

**D3 = B — Withdrawal cascade marks derived assets as `tainted`.**
When a source input is withdrawn, derived assets are not deleted
(that breaks the audit chain) — they are flipped to `state:
tainted`. Compliant runtimes MUST refuse to use tainted assets. The
issuer MAY ship a clean retrained successor in a new version that
supersedes the tainted one.

**D4 = C + (a) + (c) — Three-party-any memorial trigger, default
read-only loadable, executor may extend; plus 7-day dispute period.**
Death-certificate-only triggers (option B) are too slow for cases
where executors need immediate control. We accept that any of
executor / next-of-kin / court-order can flip the package to
memorial, with abuse mitigated by a 7-day **dispute period**: during
those 7 days, the subject can reverse-attest via the v0.6
`withdrawal_endpoint`, which un-freezes the package and reverse-locks
the malicious trigger. After the dispute window passes, the
`.life` becomes read-only loadable (so families can still talk),
and the executor MAY sign new versions under additional scrutiny
(memorial events, archival publishing, etc.).

**D5 = C — Soft re-consent reminder, not a hard wall.**
The hard `expires_at` (v0.7) still applies as the actual block. A new
soft field `recommended_re_consent_after` lets the issuer say "after
N months I would like to re-consent," and runtimes show a reminder
banner. Loaders may still interact normally during the soft window.

### 3.4 What is left out

- Cross-package merges and federation are explicitly out of scope.
- Lifecycle does NOT define how a court order is verified (legal
  process is a runtime / institution responsibility).
- Mutation logs do NOT replace audit events; they are a denormalised
  per-asset view.

---

## 4. Topic 3 — Asset Binding

### 4.1 Problem

A `.life` package is a heap of assets and metadata. Without a "user
manual," runtimes guess: which voice file should TTS load? Which
atoms file is the memory backend? Which constraints are absolute? What
UI shape is mandatory? Different runtimes give different answers, and
issuer intent gets lost.

### 4.2 Solution

A new file `binding/runtime_binding.json` declares the contract
between a `.life` and any compliant runtime:

```json
{
  "binding_version": "0.1.0",
  "minimum_runtime_version": "0.1",

  "capabilities": {
    "voice_synthesis": {
      "asset_id": "voice-master-v1",
      "engine_compatibility": [
        { "name": "tortoise-tts", "version_range": ">=2.4 <3.0", "strict": true }
      ],
      "params": { "sample_rate": 24000, "vocoder": "univnet" }
    }
  },

  "orchestration": {
    "default_llm": { "name": "any_compatible", "version_range": "*" },
    "minimum_llm_capabilities": ["chat", "function_calling"],
    "context_strategy": "rolling_window",
    "max_context_tokens": 8000
  },

  "hard_constraints": {
    "no_image_generation": true,
    "no_video_generation": true,
    "no_voice_clone_for_third_party": true,
    "max_memory_horizon_days": 365,
    "max_concurrent_sessions": 1,
    "geo_restrictions": []
  },

  "surface": {
    "supported": ["chat", "voice_chat", "avatar_2d"],
    "minimum_required": "chat",
    "preferred": "voice_chat",
    "ui_hints": { "disclosure_label": "...", "color_scheme": "...", "avatar_image_ref": "..." }
  },

  "hosted_api_preference": {
    "allowed": true,
    "preferred_for": ["voice_synthesis"],
    "must_be_local_for": ["memory_recall"],
    "providers_whitelist_ref": "policy/hosted_api.json"
  }
}
```

### 4.3 Decisions

**D1 = C — Hybrid capability vocabulary.**
A fixed core enum of ~20 capabilities (`voice_synthesis`,
`voice_recognition`, `memory_recall`, `persona`, `knowledge_qa`,
`image_recall`, `video_recall`, `chat`, `agent_tool_use`, `planning`,
…) gives runtimes a stable target. The `x-` prefix lets ecosystems
declare experimental capabilities without touching the spec. Runtimes
that do not understand an `x-` capability simply do not bind it.

**D2 = C — `engine_compatibility[].strict` is issuer-controlled.**
`strict = true` (the schema default) means semver range is honoured
literally; a major-version bump on the engine breaks the binding. `strict
= false` lets the runtime relax to a semver-compatible interface
match. We considered (A) always-strict and (B) interface-only; both
produced too much returned breakage on real ML engines. Issuer
self-decision is the realistic compromise.

**D3 → replaced by the tier system (see section 5).**
The original D3 — "who decides fallback?" — is no longer a binding
question. Fallback aggressiveness is a function of tier: low-tier
packages auto-fallback freely; high-tier packages refuse to load
unless their declared engines are exactly available.

**D4 = C — Hybrid `hard_constraints` keys with fail-close.**
Core ~30 constraints (`no_*` patterns plus `max_*`, `min_*`,
`geo_restrictions`, …) are spec-defined. The `x-` prefix is allowed
for ecosystem extensions. The critical rule: runtimes that do **not**
understand an unknown constraint key MUST refuse to load (fail-close).
Silently ignoring an issuer's prohibition is unacceptable.

**D5 = A — Hosted-API gating is AND of binding and policy.**
`binding.hosted_api_preference.allowed = true` says the issuer
designed the package to use cloud. `policy/hosted_api.json` (the v0.6
opt-in gate) says the user authorises specific providers. Hosted
calls happen only when *both* sides agree. This preserves the v0.6
opt-in without adding a third concept.

### 4.4 What is left out

- Binding does NOT specify *how* providers implement the engine
  interface — that is `LifeCapabilityProvider` (section 6).
- Binding does NOT enforce that issuer claims about engine
  compatibility are correct — runtimes must verify at load time.
- Binding does NOT model multi-modal pipelines beyond capability
  declarations (e.g. the wiring from STT → LLM → TTS is the
  runtime's orchestration responsibility).

---

## 5. Topic 3 — Tier System (multi-dimensional credit rating)

### 5.1 Problem

A loader with a `.life` in hand needs a single quick signal: how much
should I trust this? How much detail does it have? How much consent is
attached? The v0.7 `verification_level` field answered only one
question (identity). It is too coarse to drive the fallback,
ranking, registry-filtering, and runtime-policy decisions a real
ecosystem needs.

### 5.2 Solution

Replace `verification_level` with a multi-dimensional `tier` block,
auto-computed by the builder. Six independent dimensions feed a
weighted score (0–100), which lands in one of 12 named tiers
(Cosmic Evolution naming, see appendix A).

```json
{
  "tier": {
    "score": 67,
    "level": "VII",
    "name": "Main Sequence",
    "glyph": "★",
    "dimensions": {
      "identity_verification": "kyc_verified",
      "asset_completeness": "comprehensive",
      "consent_completeness": "notarized",
      "detail_level": "high_fidelity",
      "audit_chain_strength": "signed_chain",
      "jurisdiction_clarity": "declared"
    },
    "computed_at": "2026-04-26T14:00:00Z",
    "computed_by": "tools/build_life_package.py@0.2.0"
  }
}
```

### 5.3 Six dimensions

| # | Dimension | Levels (low → high) |
|---|---|---|
| 1 | `identity_verification` | unverified → self_attested → email_verified → id_verified → kyc_verified → notarized |
| 2 | `asset_completeness` | minimal → partial → standard → comprehensive → archive_grade |
| 3 | `consent_completeness` | none → text_only → signed → notarized → multi_party_attested |
| 4 | `detail_level` | low_fidelity → medium → high_fidelity → cinematic |
| 5 | `audit_chain_strength` | minimal → linked → signed_chain → notarized_chain |
| 6 | `jurisdiction_clarity` | unspecified → declared → cross_validated → court_recognized |

Default weights: `consent_completeness` ×2, `identity_verification` ×2,
others ×1. Score normalised 0–100. Tier mapping table in appendix A.

### 5.4 Design rules

- Tier is **fully public** in `life-package.json`. A `.life`'s tier is
  its credit rating; opacity destroys trust.
- Builder **MUST auto-compute** `score`, `level`, and `dimensions`.
  Hand-filled tier blocks are rejected at validation.
- The spec **freezes** the machine fields (`score`, `level`,
  `dimensions`). The `name` and `glyph` belong to a versioned naming
  appendix that can evolve without bumping the spec major.
- Back-compat: a v0.7 `verification_level` field is still accepted as
  an alias for `tier.dimensions.identity_verification`.
- The tier replaces the original Topic-3 D3 fallback decision.
  Low-tier packages auto-fall-back to built-in providers; high-tier
  packages refuse to load when their declared engines are missing.

### 5.5 What is left out

- Cross-package tier comparison is **subjective**: a Tier-IX
  `.life` of person A and a Tier-IX `.life` of person B are not
  interchangeable.
- Tier does NOT model issuer reputation history or registry
  trustworthiness; those are deferred to v1.0+ when a registry
  protocol exists.

---

## 6. Topic 4 — Assembly / one-click launch

### 6.1 Problem

The v0.7 runtime spec defined an 8-step *load* sequence. That answers
"how do I open a `.life`" but not "how do I run it" — provider
registration, sandboxing, fallback, hosted-vs-offline policy, OS
bootstrap, and post-launch monitoring were undefined.

### 6.2 Solution

A 5-stage assembly pipeline replaces (and absorbs) the 8-step load
sequence:

1. **Verify** — sha256 + JSON Schema + signature + `expires_at` +
   `lifecycle_state` + withdrawal ping + audit chain. Any failure is
   fail-close.
2. **Resolve** — read `binding.capabilities` and `tier`; consult the
   Provider Registry; tier-driven graceful degradation (low tier
   auto-fallback, high tier strict-or-refuse).
3. **Assemble** — instantiate providers, inject `hard_constraints`,
   inject the disclosure label, emit a `capability_bound` audit
   event.
4. **Run** — start the surface (chat / voice / avatar / 3D); filter
   inputs and outputs through `forbidden_uses[]`; prefix outputs with
   the disclosure label.
5. **Guard** — three background watchers: withdrawal poll (≥24h),
   memorial state changes, expiry approach; plus a continuous audit
   emitter.

A **Provider Registry** at `~/.dlrs/providers/<provider_name>/` holds
installable adapters. Each provider implements the
`LifeCapabilityProvider` interface:

```
LifeCapabilityProvider {
  capability,
  name,
  version,
  engine_compatibility_id,
  supports(binding) -> bool,
  load(asset_paths, binding) -> instance,
  teardown(instance) -> void
}
```

### 6.3 Decisions

**D1 = C — Graded sandbox.**
Built-in providers (shipped with the runtime) and user-installed
providers (installed via `lifectl` or an OS package manager) run as
ordinary OS processes; trust comes from the install path. Future
`.life`-bundled providers MUST be sandboxed (wasm / firejail / nsjail)
or refused outright; bundled code is never trusted by virtue of being
inside a `.life`.

**D2 = B (v0.8) + C (v1.0+) — `.life` cannot bundle provider code in
v0.8; trusted issuer whitelist may permit it later.**
Allowing arbitrary bundled provider code in v0.8 would import every
sandbox-escape attack into the format on day one. Until a community
trusted-issuer mechanism (with revocation and a reputation chain)
exists, providers come from sources outside the `.life`. v1.0+ may
revisit.

**D3 = Hybrid — pure cloud is acceptable; offline is recommended,
not mandatory; both modes are first-class; default is per-user.**
Some `.life` packages will be too compute-heavy for consumer hardware
(large multimodal models, real-time avatar rendering). Forcing
offline-fallback as a spec mandate would block them from existing.
Instead, both pure-cloud and offline-capable packages are first-class.
The AND-gate from Binding D5 still applies (issuer + user must both
allow). When both sides are silent, the runtime's per-user
configuration decides — the spec does not pick a default.

**D4 = C — Three-field surface declaration.**
`supported[]` lists every UI shape a `.life` can render in.
`minimum_required` is the floor: a runtime that cannot satisfy this
refuses to load. `preferred` is the recommendation. This matches the
Binding spec.

**D5 = C — Bootstrap via OS package manager.**
`brew install dlrs-runtime` / `apt install dlrs-runtime` / `winget
install dlrs-runtime`. `.life` files **never** carry installer
code. First-time-user friction (the user must know to install the
runtime before double-clicking) is accepted as the price of not
shipping a self-extracting executable inside every `.life`.

### 6.4 What is left out

- v0.8 ships **spec only**. The first real `dlrs-runtime` is a v0.9
  deliverable.
- Provider distribution (a `lifectl` CLI, a registry, the `life://`
  URI) is deferred to v0.10+.
- OS-level file association and a GUI launcher are deferred to v0.11+.

---

## 7. Cross-topic dependencies

| Edge | What flows | Required because |
|---|---|---|
| Genesis → Lifecycle | `source_inputs[].ref` → `cascade_index.source_to_derived` keys | A withdrawal event needs to find every derived asset |
| Genesis → Binding | `method.name` → `engine_compatibility[].name` constraint | Issuer must not bind to an engine that cannot read the asset format |
| Genesis → Assembly | `compute.hosted_api_used` → loader trust signal | Loader needs to know whether data has already left the local boundary |
| Lifecycle → Binding | `lifecycle.state` → bind / refuse decision | Tainted, withdrawn, or superseded assets must not be bound |
| Lifecycle → Assembly | `lifecycle_state` (package), `frozen`, `memorial_metadata` → stage 1 verify | Verify must reject withdrawn / expired packages and apply memorial read-only policy |
| Binding → Assembly | The whole binding file is the input to stage 2 (Resolve) | Binding *is* the assembly contract |
| Tier → Binding | Drives fallback aggressiveness | Replaces the old D3 fallback decision |
| Tier → Assembly | Drives stage 2 (Resolve) graceful degradation | Low-tier auto-fallback, high-tier strict-or-refuse |

---

## 8. Roadmap (where each spec lands)

| Milestone | Deliverable |
|---|---|
| v0.8 (this epic) | The five spec documents and schemas listed above |
| v0.9 | First `dlrs-runtime` reference implementation; ≥4 built-in providers |
| v0.10 | Provider distribution: `lifectl` CLI, registry protocol, `life://` URI |
| v0.11+ | GUI launcher, OS file association, encrypted-mode tooling, trusted-issuer whitelist |

---

## Appendix A — Schema D Cosmic Evolution naming registry

Twelve tiers from sub-atomic to cosmological, ordered by emergent
complexity. This appendix is versioned independently from the spec
core; the machine-readable `level` (Roman numeral I–XII) is the
stable identifier.

| Tier | Roman | Name | Glyph | Score range |
|------|------:|-------------------|:----:|:-----------:|
| 1    | I     | Quark             | ⋅    | 0–8         |
| 2    | II    | Atom              | ⊙    | 9–16        |
| 3    | III   | Molecule          | ⋮⋮   | 17–24       |
| 4    | IV    | Stardust          | ✧    | 25–32       |
| 5    | V     | Nebula            | 🌫    | 33–40       |
| 6    | VI    | Protostar         | ✦    | 41–50       |
| 7    | VII   | Main Sequence     | ★    | 51–60       |
| 8    | VIII  | Red Giant         | ◉    | 61–68       |
| 9    | IX    | White Dwarf       | ⚪    | 69–76       |
| 10   | X     | Neutron Star      | ⚫    | 77–84       |
| 11   | XI    | Pulsar            | ◎    | 85–92       |
| 12   | XII   | Singularity       | ●    | 93–100      |

A "Tier VII Main Sequence ★" `.life` is a healthy, comprehensive,
notarised package — the social-target tier the ecosystem should
reward. Tier XII is reserved for the rare end-to-end notarised
archive-grade case.

---

## Appendix B — Memorial dispute period

When any of executor / next-of-kin / court order flips the package to
`lifecycle_state: memorial`, the following machine-checkable rules apply:

1. Compliant runtimes MUST treat the package as read-only loadable
   *immediately* (option a from D4).
2. For **7 days** following the trigger, runtimes MUST poll the
   package's `withdrawal_endpoint` for a `still_alive_attestation`
   counter-signal carrying the subject's signature.
3. A valid `still_alive_attestation` un-freezes the package and writes
   a memorial-trigger-disputed event to the audit chain. The
   triggering party is reverse-locked: subsequent triggers from that
   party require multi-party signatures.
4. After 7 days without a dispute, the memorial state is final.
   Executor-extension (option c from D4) becomes available; each
   extension MUST carry an additional executor signature plus the
   audit chain entry.

---

## Appendix C — Rejected alternatives (preserved for institutional memory)

These options were considered and rejected during the discussion. They
are recorded so future contributors do not re-litigate them without
new evidence.

### C.1 Genesis (Topic 1)

- **D1 (A)**: declare base model as a static field but do NOT list it
  as a virtual asset. *Rejected:* breaks self-describing-ness; loaders
  cannot verify base-model sha256 against a download.
- **D1 (B)**: do not require base-model declaration. *Rejected:*
  license compliance becomes invisible.
- **D2 (A)**: hosted-API use is fatal. *Rejected:* excludes essentially
  every realistic high-quality `.life`.
- **D2 (C)**: bind hosted-API fatality to the v0.6 hosted_api gate's
  whitelist. *Rejected:* over-couples Genesis to a runtime-side
  policy file.
- **D3 (A)**: require bit-identical reproducibility. *Rejected:* most
  ML training cannot meet this bar.
- **D3 (B)**: require only "weak" reproducibility (method + inputs +
  seed). *Rejected:* loses the loader's ability to gauge trust.
- **D4 (B)**: free-text consent scope. *Rejected:* every issuer would
  invent a private vocabulary.
- **D4 (C)**: URI-scheme consent scope. *Rejected:* over-engineered
  for a finite vocabulary.
- **D5 (A)**: inline genesis inside the descriptor. *Rejected:*
  descriptors become huge; runtime load slows; withdrawal-cascade
  diffs are noisy.
- **D5 (C)**: split summary inline + full ref. *Rejected:* spec must
  prevent summary/full disagreement; complexity not worth the win.

### C.2 Lifecycle (Topic 2)

- **D1 (A) Semver only.** *Rejected:* hash collisions and renames make
  semver unsafe as machine identity.
- **D1 (B) Hash only.** *Rejected:* unreadable for humans.
- **D1 (C) Monotonic counter.** *Rejected:* cannot express "minor patch
  vs major retrain."
- **D2 (A) Strictly linear supersedes.** *Rejected:* cannot model the
  realistic "public chat fork" + "medical fork" case.
- **D2 (B) Full DAG (fork + merge).** *Rejected:* merging silently
  combines permission sets (a class of attack).
- **D3 (A) Hard delete derived assets on cascade.** *Rejected:*
  destroys the audit chain.
- **D3 (C) Tainted with grace period for re-issue.** *Rejected:*
  ambiguous loader behaviour during the grace window.
- **D3 (D) Per-asset policy.** *Rejected:* gives issuers too much room
  to weaken cascade strength.
- **D4 (A) Executor-only memorial trigger.** *Rejected:* delays
  legitimate post-mortem control when no executor exists.
- **D4 (B) Death certificate strictly required.** *Rejected:* legal
  variation across jurisdictions makes this unreliable; runtime
  cannot verify a JPG of a death certificate machine-readably.
- **D4 (b) Read-only display only (no conversation).** *Rejected:* the
  "talk one more time" use case is a primary motivation for `.life`.
- **D5 (A) No drift detection.** *Rejected:* loaders need at least a
  reminder.
- **D5 (B) Hard expiry only.** *Rejected:* already in v0.7; this
  question is about the *soft* signal.
- **D5 (D) Hard expiry + soft reminder both required.** *Rejected:*
  redundant; v0.7 already handles hard expiry. The new field adds
  only the soft reminder.

### C.3 Binding (Topic 3)

- **D1 (A) Fixed enum only.** *Rejected:* too restrictive for
  ecosystem experimentation.
- **D1 (B) URI-scheme capabilities.** *Rejected:* over-engineered.
- **D2 (A) Always strict.** *Rejected:* every engine major bump
  invalidates real `.life` packages.
- **D2 (B) Interface-match always.** *Rejected:* requires a
  `LIFE_ENGINE_INTERFACE.md` for every capability.
- **D4 (A) Fully fixed `hard_constraints` keys.** *Rejected:* blocks
  ecosystem experimentation.
- **D4 (B) Fully free constraint keys with fail-close.** *Rejected:*
  no shared vocabulary makes interop impossible.
- **D5 (B) Binding fully replaces hosted-API policy.** *Rejected:*
  loses user-side opt-in.
- **D5 (C) Binding does not participate in hosted decisions.**
  *Rejected:* loses issuer-side opt-in.

#### Tier naming alternatives

The user explicitly chose "和星空有关的吧" — anything related to the
starry sky. Cosmic Evolution (Schema D) was selected. Three other
serious schemas were considered:

- **Moon phases** (New Moon → Eclipse): rejected because it carries
  cultural overtones (lunar calendar, astrology) that may not
  translate.
- **Minerals** (Talc → Carbonado, Mohs hardness 1 → 10+): rejected as
  off-theme (user wanted sci-fi / data, not geology).
- **Pure geometric symbols** (◇ / △ / □ / ⬠ / …): rejected as too
  abstract and not memorable for social use.
- **Schema E — Data Architecture** (Bit → Singularity, all data-
  structure terms): rejected because the lower tiers (Bit, Nibble,
  Byte) felt too low-level for a social-facing concept.
- **Schema F — Hybrid Data → Cosmic** (Bit → Tensor → Galaxy →
  Singularity): rejected in favour of full cosmic per the user's "和
  星空有关的吧" preference.

### C.4 Assembly (Topic 4)

- **D1 (A) OS-process only for everything.** *Rejected:* leaves no
  safe path for future bundled providers.
- **D1 (B) Mandatory sandbox for every provider.** *Rejected:* blocks
  GPU access, severely impacts performance.
- **D2 (A) Allow bundled provider code in v0.8.** *Rejected:*
  imports every sandbox-escape attack on day one.
- **D3 (A) Spec-mandated offline-only baseline.** *Rejected:* excludes
  legitimately compute-heavy `.life` packages.
- **D3 (B) Cloud-first.** *Rejected:* makes long-term archival
  packages dependent on services that may disappear.
- **D5 (A) OS file-association installer flow.** *Rejected:* clutters
  the attack surface (any `.life` could social-engineer an installer
  download). Package-manager-only is more conservative.
- **D5 (B) `.life`-bundled bootstrap stub.** *Rejected:* obvious
  malware vector.

---

## Appendix D — Discussion timeline (for archival completeness)

The four-topic architecture discussion ran on 2026-04-26 in a single
draft-and-iterate session. The user (BELLO) chose discussion mode "C"
(mixed: drafts proposed by Devin, decision points marked, user picks
or refines, iterate). Five decision points per topic plus the
inserted tier system. Notes were persisted continuously to
`/home/ubuntu/.life-v0.8-architecture-notes.md` during the session
and are mirrored into this document at PR time.

