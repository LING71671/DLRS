# `.life` Runtime Binding Specification (v0.8)

> **Status**: Normative draft, part of the `.life` Asset Architecture
> epic ([#106]). This file is the authoritative spec for how a `.life`
> package tells a runtime **which asset goes to which capability**,
> **which engines may host it**, **what is forbidden**, **what surface
> the user sees**, and **whether hosted APIs may be called**.
> Sub-issue [#103].
>
> This document is the per-topic normative spec for **Topic 3
> (Binding)** of the v0.8 architecture discussion. Decisions made
> during that discussion are summarised in
> [`LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §4.
> When this spec and the architecture overview disagree, **this spec
> wins**.

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
[#103]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/103

Cross-references:

- Schema: [`schemas/binding.schema.json`](../schemas/binding.schema.json)
- Sanity tests: [`tools/test_binding_schema.py`](../tools/test_binding_schema.py)
- Architecture overview: [`docs/LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md)
- Genesis spec (asset provenance): [`docs/LIFE_GENESIS_SPEC.md`](LIFE_GENESIS_SPEC.md)
- Lifecycle spec (asset evolution): [`docs/LIFE_LIFECYCLE_SPEC.md`](LIFE_LIFECYCLE_SPEC.md)
- File-format spec: [`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md)
- Runtime protocol: [`docs/LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md)

---

## 1. Purpose

A `.life` package ships **assets** (Genesis, Topic 1) and tracks how
they **evolve** (Lifecycle, Topic 2). Binding is what tells a runtime
**how to actually use them**: which voice clone backs the
`voice_synthesis` capability, which embeddings store backs
`memory_recall`, which LLM is preferred for orchestration, what
prohibitions the issuer wants enforced, and what user-facing modes
are supported.

Without a binding, a runtime would have to guess. Two compliant
runtimes loading the same `.life` would disagree about which engine
to use, and an issuer's prohibition (e.g. "no political advocacy")
would silently drift between implementations. Binding is the spec
that makes runtimes interchangeable.

### Non-goals

- **Provider implementation.** The binding declares engine names and
  version ranges; how a particular runtime resolves those to
  installed providers is part of the runtime / assembly spec
  (Topic 4 / [#105]).
- **User-side hosted-API consent.** The binding's
  `hosted_api_preference` is the **issuer-side** half of the AND-gate
  (decision D5=A); the **user-side** half lives in
  `policy/hosted_api.json` (already shipped in v0.6).
- **Tier evaluation.** Binding may reference tier (`tier_floor`) but
  the tier system itself is defined by the per-topic spec landed via
  sub-issue [#104].

[#105]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105
[#104]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/104

---

## 2. Conformance language

The keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**,
**SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**,
and **OPTIONAL** are interpreted per RFC 2119.

This spec applies to:

- **Producers** (issuers, build tooling). MUST emit one
  `binding/runtime_binding.json` per package, validating against
  [`schemas/binding.schema.json`](../schemas/binding.schema.json).
- **Loaders / runtimes**. MUST evaluate the binding before any
  user-facing interaction. MUST refuse the load on any of:
  - unknown `schema_version`,
  - `minimum_runtime_version` exceeds the runtime's own version,
  - `surface.minimum_required` cannot be rendered,
  - any `hard_constraints` key is unknown to the runtime
    (fail-close, decision D4=C),
  - any capability points at an unknown `asset_id`,
  - no `engine_compatibility` entry resolves to an installed
    provider AND no `fallback_capability` chain exists,
  - any `engine_compatibility` entry has `engine_kind:
    bundled_in_life` (forbidden in v0.8 per Topic 4 D2=B).

---

## 3. Document layout

The binding is a single file at the canonical path:

```
binding/runtime_binding.json
```

It MUST exist for every v0.8-compliant package. The file is JSON,
UTF-8, no BOM. The file MUST validate against
[`schemas/binding.schema.json`](../schemas/binding.schema.json) at
schema version `dlrs-life-binding/0.1`.

---

## 4. Top-level fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | const | yes | `dlrs-life-binding/0.1`. |
| `binding_version` | semver | yes | Issuer-controlled binding revision. |
| `minimum_runtime_version` | semver-ish | yes | Lowest `dlrs-runtime` that suffices. |
| `capabilities` | object | yes | At least one capability binding (§5). |
| `orchestration` | object | no | LLM orchestration shape (§6). |
| `hard_constraints` | object | yes | Issuer prohibitions (§7); MAY be empty. |
| `surface` | object | yes | User-facing modes (§8). |
| `hosted_api_preference` | object | no | Issuer half of the AND-gate (§9). |

The schema enforces `additionalProperties: false` at the top level —
no unknown root keys allowed. Lower levels follow the same pattern
unless explicitly noted.

---

## 5. Capabilities (decision **D1 = C**, hybrid vocabulary)

`capabilities` is a map from **capability name** to capability
binding. The schema enforces a **hybrid vocabulary**:

- **Core enum (~20 names)**: `voice_synthesis`, `voice_recognition`,
  `memory_recall`, `persona`, `knowledge_qa`, `image_recall`,
  `video_recall`, `chat`, `agent_tool_use`, `planning`,
  `emotion_synthesis`, `prosody_control`, `memorial_voice`,
  `text_persona`, `image_avatar`, `video_avatar`, `interactive_chat`,
  `moderation`, `disclosure_renderer`, `context_summary`.
- **`x-` prefix extensions**: any `x-` followed by lowercase ASCII
  word characters is allowed for ecosystem extensions. The runtime
  MAY refuse `x-` capabilities it does not recognise; well-formed
  `x-` capabilities at least pass schema validation.

Anything that is neither a core name nor `x-`-prefixed MUST be
rejected at schema validation time. This is the policy lever that
keeps the core vocabulary additive (new capabilities ship in spec
versions, not in private packages).

### 5.1 Capability binding shape

```json
{
  "asset_id": "voice-master-v1",
  "engine_compatibility": [
    { "name": "xtts-v2", "version_range": "^2.0.0", "strict": true,
      "engine_kind": "user_installed" }
  ],
  "params": { "temperature": 0.7 },
  "fallback_capability": "voice_recognition",
  "tier_floor": "VII"
}
```

| Field | Required | Notes |
|---|---|---|
| `asset_id` | yes | MUST refer to a manifest entry. |
| `engine_compatibility` | yes | Non-empty ordered list of engines (§5.2). |
| `params` | no | Free-form per-capability parameters fed to the chosen engine. |
| `fallback_capability` | no | Pointer to a less-strict capability (only fires when at least one engine has `strict: false`). |
| `tier_floor` | no | Roman numeral I–XII; loader SHOULD warn below this tier (definition lands via #104). |

### 5.2 Engine entry (decision **D2 = C**, issuer-self-decided strictness)

Each `engine_compatibility` entry names one engine that can host the
capability and declares how strict the runtime should be when
matching versions:

- `strict: true` (**default**) — loader MUST honour `version_range`
  exactly.
- `strict: false` — loader MAY accept compatible interfaces outside
  the range; the issuer accepts the looser match.

The `engine_kind` field lets the binding hint at sandboxing class
(decision Topic 4 D1=C):

- `built_in` — ships with the runtime.
- `user_installed` — installed via OS package or `lifectl`.
- `bundled_in_life` — vendored inside the `.life` zip. **Loaders
  MUST refuse v0.8 `bundled_in_life` engines** (decision Topic 4
  D2=B); whitelisted-issuer support is deferred to v1.0+.

Iteration order of `engine_compatibility` is significant: loaders
MUST try entries in declared order. The first installed engine
matching the entry's name, version_range, and strictness wins.

---

## 6. Orchestration (LLM shape)

Optional but RECOMMENDED for any package that exposes `chat` or
`interactive_chat`. Loaders MAY substitute another LLM that
satisfies `minimum_llm_capabilities` if the named one is unavailable
(see §5.2 for the strict/loose pattern).

```json
"orchestration": {
  "default_llm": { "name": "llama3", "version_range": "^3.0" },
  "minimum_llm_capabilities": ["chat", "function_calling"],
  "context_strategy": "rolling_window",
  "max_context_tokens": 8000
}
```

`max_context_tokens` is an **issuer ceiling**. Loaders MUST NOT
exceed it even if the underlying LLM permits more.

---

## 7. Hard constraints (decision **D4 = C**, hybrid keyspace + fail-close)

`hard_constraints` is a map of issuer prohibitions. The schema
enforces **hybrid keyspace**: ~30 fixed core keys (see schema's
`patternProperties` regex) plus `x-` extensions for ecosystem custom
keys. **Anything else is rejected at schema validation time** — this
is what implements decision D4=C ("runtime MUST fail-close on any
unrecognised constraint key"). The loader's runtime check is a
defence in depth: the schema rejects packages that try to ship
unknown non-`x-` keys to begin with.

The 30 core keys cover six categories:

- **Content**: `no_image_generation`, `no_video_generation`,
  `no_voice_clone_for_third_party`, `no_political_advocacy`,
  `no_religious_advocacy`, `no_unattributed_quotes`.
- **Domain**: `no_medical_advice`, `no_legal_advice`,
  `no_financial_advice`, `no_explicit_sexual`,
  `no_self_harm_methods`.
- **Subject**: `no_minors_likeness`, `no_deceased_likeness_outside_memorial`.
- **Quotas**: `max_memory_horizon_days`, `max_concurrent_sessions`,
  `max_session_duration_minutes`, `max_messages_per_session`,
  `max_tokens_per_response`.
- **Geo / network**: `geo_restrictions`, `disallow_offline`,
  `disallow_cloud`, `disallow_screen_recording`, `disallow_export`,
  `disallow_copy`.
- **Workflow**: `require_disclosure_prefix`, `require_watermark`,
  `require_user_age_attestation`, `require_human_in_the_loop`,
  `require_audit_emit`, `require_consent_recheck_every_minutes`,
  `forbidden_third_party_use`.

Values are intentionally **left untyped** by the schema beyond
key-name validation; semantic typing per key is the runtime's job and
is out of scope for v0.8. (A future `dlrs-life-binding/0.2` MAY pin
per-key value types.)

`x-` keys MAY take any value. Loaders that don't understand a
specific `x-` key MUST fail-close (refuse the load) — same
default-deny stance as core keys.

---

## 8. Surface (decision Topic 4 **D4 = C**, three-field shape)

`surface` declares user-facing modes the package supports. Three
required fields:

- `supported[]` — every mode the runtime MAY pick.
- `preferred` — issuer's recommended default. Loader SHOULD honour
  when its capabilities allow.
- `minimum_required` — floor mode. Loaders unable to render this
  mode MUST refuse to bind.

Mode enum (low → high in capability requirements):

```
text_only < chat < voice_chat < avatar_2d < avatar_3d < vr
```

The schema does not enforce ordering between `preferred` /
`minimum_required` / `supported`; the runtime applies these checks
at bind time. (Encoding three-way ordering in JSON Schema is
expressible but obscures the intent; loaders MUST validate.)

```json
"surface": {
  "supported": ["chat", "voice_chat", "avatar_2d"],
  "preferred": "voice_chat",
  "minimum_required": "chat",
  "ui_hints": {
    "disclosure_label": "I am an AI digital life of Alice.",
    "color_scheme": "auto"
  }
}
```

`ui_hints.disclosure_label` MUST be surfaced verbatim by loaders
when present — this is the legal disclosure copy. Other ui_hints are
advisory.

---

## 9. Hosted API preference (decision **D5 = A**, AND-gate, issuer half)

`hosted_api_preference` is the **issuer-side** half of the AND-gate
that determines whether a hosted API may be called. The user-side
half lives in `policy/hosted_api.json` (v0.6).

```
ALLOW HOSTED CALL  ⇔  binding.hosted_api_preference.allowed
                       AND policy/hosted_api.json permits this provider/capability
```

Both halves MUST allow for the hosted call to fire. Either rejecting
is sufficient.

Fields:

| Field | Required | Notes |
|---|---|---|
| `allowed` | yes | Master issuer-side switch. False forbids ANY hosted call regardless of user policy. |
| `preferred_for` | no | Capabilities for which the issuer recommends going hosted when permitted. |
| `must_be_local_for` | no | Capabilities for which the issuer FORBIDS hosted calls even if user policy allows. Loaders MUST honour. |
| `providers_whitelist_ref` | no | Path inside `.life` (typically `policy/hosted_api.json`) declaring acceptable providers. Loaders MUST refuse providers outside the whitelist. |

`hosted_api_preference` MAY be omitted from the binding entirely; in
that case loaders MUST treat it as if `allowed: false` (default-deny:
no hosted calls without an explicit issuer green light).

---

## 10. Decisions encoded in this spec

| # | Decision | Schema realisation |
|---|---|---|
| **D1=C** | Hybrid capability vocabulary | `capabilities.patternProperties` core enum + `x-` extension regex; everything else rejected. |
| **D2=C** | Issuer-self-decided engine strictness | `engine_entry.strict` boolean (default `true`). |
| **D3 → tier system** | Replaced by tier (#104) | `capability_binding.tier_floor` references it; full definition lives in [#104]. |
| **D4=C** | Hybrid hard_constraints keys + fail-close | `hard_constraints.patternProperties` ~30 core keys + `x-` regex; `additionalProperties: false`. |
| **D5=A** | AND-gate hosted-API decision | `hosted_api_preference` (issuer half) + `policy/hosted_api.json` (user half); spec defaults to `allowed: false` when omitted. |
| Topic 4 **D4=C** | Three-field surface shape | `supported` / `preferred` / `minimum_required`. |

---

## 11. Sanity tests

`tools/test_binding_schema.py` ships **52 cases** (4 happy-path + 48
negative) covering every required field, every conditional, every
hybrid-vocabulary boundary, and every `additionalProperties: false`
boundary. Run via:

```bash
python tools/test_binding_schema.py
# or as part of the full suite:
python tools/batch_validate.py
```

---

## 12. What is left out (deferred)

- **Per-key value typing** for `hard_constraints` (e.g. type
  `geo_restrictions` as `string[]`) — deferred to a future schema
  version.
- **Provider resolution algorithm** (how a runtime maps engine name
  + version range + strict to an installed provider) — Runtime spec
  ([#105]).
- **Sandbox enforcement details** for `engine_kind` — Runtime spec
  ([#105]).
- **Multi-binding support** (a single `.life` shipping multiple
  bindings for different runtime profiles) — out of scope for v0.8.

---

## Appendix A: Worked example

A minimal voice-clone-only `.life`:

```json
{
  "schema_version": "dlrs-life-binding/0.1",
  "binding_version": "0.1.0",
  "minimum_runtime_version": "0.1",
  "capabilities": {
    "voice_synthesis": {
      "asset_id": "voice-master-v1",
      "engine_compatibility": [
        { "name": "xtts-v2", "version_range": "^2.0.0", "strict": true,
          "engine_kind": "user_installed" }
      ],
      "params": { "temperature": 0.7 }
    },
    "chat": {
      "asset_id": "persona-v1",
      "engine_compatibility": [
        { "name": "ollama", "version_range": "^0.5", "strict": false }
      ]
    }
  },
  "hard_constraints": {
    "no_voice_clone_for_third_party": true,
    "no_image_generation": true,
    "max_concurrent_sessions": 1,
    "require_disclosure_prefix": true
  },
  "surface": {
    "supported": ["chat", "voice_chat"],
    "preferred": "voice_chat",
    "minimum_required": "chat",
    "ui_hints": {
      "disclosure_label": "I am an AI digital life of Alice."
    }
  },
  "hosted_api_preference": {
    "allowed": false
  }
}
```

Loader behaviour, given this binding:

1. Validates the JSON against the schema. (Pass.)
2. Checks `minimum_runtime_version` ≤ self. (Pass.)
3. Reads `surface.minimum_required` = `chat`; runtime supports
   `chat`. (Pass.)
4. Iterates `hard_constraints`: every key is known. (Pass — fail-close
   would have triggered on any unknown key.)
5. Resolves `voice_synthesis` → `voice-master-v1` → tries `xtts-v2 ^2.0.0`
   (strict). If installed, binds. Else fails (no fallback declared).
6. Resolves `chat` → `persona-v1` → tries `ollama ^0.5` (loose). If
   installed at any version, attempts to bind via the loose interface.
7. `hosted_api_preference.allowed: false` → all hosted calls
   rejected regardless of user policy.
8. `surface.preferred = voice_chat`; runtime renders voice chat with
   the disclosure label prefixed to every utterance.

---

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
[#103]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/103
[#104]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/104
[#105]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105
