# `.life` Asset Genesis Specification (v0.8)

> **Status**: Normative draft, part of the `.life` Asset Architecture
> epic ([#106]). This file is the authoritative spec for how a `.life`
> package records the **provenance** of every asset it ships.
> Sub-issue [#101].
>
> This document is the per-topic normative spec for **Topic 1
> (Genesis)** of the v0.8 architecture discussion. Decisions made
> during that discussion are summarised in
> [`LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §2.
> When this spec and the architecture overview disagree, **this spec
> wins**.

[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
[#101]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/101

Cross-references:

- Schema: [`schemas/genesis.schema.json`](../schemas/genesis.schema.json)
- Sanity tests: [`tools/test_genesis_schema.py`](../tools/test_genesis_schema.py)
- Architecture overview: [`docs/LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md)
- File format spec: [`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md)
- Runtime protocol: [`docs/LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md)

---

## 1. Purpose

Every asset in a `.life` package — a voice clone, a memory atom set, a
knowledge graph, a persona adapter — is a **build artefact**. v0.7
described how to package such artefacts but offered no machine-checkable
way to answer four questions about each one:

1. **What method produced it?** (e.g. which fine-tune script, which
   pipeline, which model architecture)
2. **What inputs fed in?** (which recordings, which transcripts, which
   pretrained base model, which dataset)
3. **Where did the compute happen?** (local machine, cloud GPU, hosted
   API)
4. **Which consent scopes authorised the production?** (voice cloning?
   memorial use? commercial distribution?)

Without those answers, downstream consumers cannot perform withdrawal
cascades (revoke a single recording → mark every derived asset
tainted), reproducibility audits (re-run the build to compare), license
compatibility checks (was the base model permissively licensed?), or
hosted-API leak detection (did inputs ever leave the operator's
machine?).

This spec defines a sibling file
`genesis/<asset_id>.genesis.json` — one per asset — that answers all
four questions in a structured, schema-validated form.

---

## 2. Conformance language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and
**MAY** are to be interpreted as in [RFC 2119].

[RFC 2119]: https://www.rfc-editor.org/rfc/rfc2119

---

## 3. File location and naming

Each asset declared in `manifest/manifest.json` SHOULD have a sibling
file at the relative path:

```text
genesis/<asset_id>.genesis.json
```

Where `<asset_id>` is the asset's identifier in the manifest, lowercased
and matching the regex `^[a-z][a-z0-9_-]{2,127}$`.

Loaders MUST treat a missing genesis file for a present asset as a
**warning**, not a hard error. Issuers SHOULD ship genesis files for
every asset; loaders MAY refuse to use assets without genesis files
when the package's `tier.audit_chain_strength` is
`signed_chain` or higher (see [`LIFE_TIER_SPEC.md`](LIFE_TIER_SPEC.md)
once delivered).

Each genesis file MUST be a single JSON object validating against
[`schemas/genesis.schema.json`](../schemas/genesis.schema.json).

---

## 4. Required structure

A genesis document has ten required top-level fields:

| Field | Type | Purpose |
|---|---|---|
| `schema_version` | const string | Identifies this spec version. v0.8 = `dlrs-life-genesis/0.1`. |
| `asset_id` | string | Cross-reference into `manifest/manifest.json`. |
| `method` | object | What produced the asset. |
| `source_inputs[]` | array | What went in. |
| `compute` | object | Where and when production happened. |
| `consent_scope_checked` | object | Build-time verification that consent covered the scopes used. |
| `audit_event_ref` | string | Pointer into `audit/events.jsonl`. |
| `audit_event_id` | string | Stable id of the matching audit event. |
| `reproducibility_level` | enum | Graded reproducibility claim (D3=C). |
| `consent_scope[]` | array | Scopes the asset is authorised for (D4=A). |

Three optional fields complement the required set:
`asset_kind`, `base_model`, `notes`.

---

## 5. Decisions encoded in this spec

The architecture discussion (April 2026, see
[`LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §2.3)
locked five decisions for Genesis. This section ties each to its
schema realisation and the loader behaviour it implies.

### 5.1 D1 = C — Base pretrained models are virtual assets

A voice clone is not really *one* asset; it is a fine-tune of a base
model. The spec treats the base model as a **virtual asset** (a thing
referenced inside the package without necessarily being shipped as
bytes). This is realised in two places:

- A `source_inputs[]` entry of `type: "base_model"`, with `ref` either
  pointing to a public URL or to a sibling file inside the package,
  `sha256` of the published weights, `consent_ref` set to
  `not_applicable`, and `consent_scope` set to `["license_governed"]`.
- An optional top-level `base_model` block summarising name, license,
  and hash for fast inspection without scanning the full
  `source_inputs` array.

The two MUST be consistent when both are present (same `name`, same
`sha256`).

License compatibility (e.g. `cc-by-nc-4.0` for XTTS-v2 forbidding
commercial reuse) is NOT enforced by this spec. Loaders MAY apply
license policies of their own; the spec only requires disclosure.

### 5.2 D2 = B — `hosted_api_used` is declared but not blocking

`compute.hosted_api_used: true` is a privacy event: bytes left the
operator's machine and a third party saw them. Refusing to ingest such
packages was rejected as too restrictive: most realistic high-quality
`.life` builds touch a hosted API somewhere (transcription,
embedding, voice synthesis training).

So the spec REQUIRES disclosure (`hosted_api_used`,
`hosted_api_providers[]`) but does NOT block. Loaders weigh hosted-API
exposure through the tier system
([`LIFE_TIER_SPEC.md`](LIFE_TIER_SPEC.md), to be delivered): a build
that touched hosted APIs scores lower on `audit_chain_strength` and
`detail_level`, and may fall under `id_verified` rather than
`kyc_verified` on `identity_verification`.

The schema enforces that **`hosted_api_used: true` requires at least
one entry in `hosted_api_providers[]`**. Each provider entry names the
API by name and SHOULD include `endpoint`, `purpose`, and a link to the
provider's data-retention policy.

The build-time `compute.hosted_api_used` field is **independent** from
the runtime hosted-API gate `policy/hosted_api.json` (v0.6). The
runtime gate controls whether THIS RUNTIME may make hosted calls when
serving the asset; the build-time field records whether THE BUILD
already made hosted calls.

### 5.3 D3 = C — Graded `reproducibility_level`

Strict bit-identical reproducibility is impossible for almost all
modern ML training (CUDA non-determinism, kernel selection differences,
hardware-dependent cuDNN paths). Banning non-reproducible assets would
exclude every realistic ML pipeline.

Instead the spec defines a graded enum:

| Level | Meaning |
|---|---|
| `bit_identical` | Re-running the method with the same `source_inputs`, `code_commit`, and `config_ref` produces byte-identical output. Rare; requires deterministic kernels and pinned RNGs. |
| `param_identical` | Same training inputs and method, but model parameters may differ across runs due to non-deterministic GPU kernels. The standard claim for fine-tuning on consumer GPUs. |
| `not_reproducible` | Retraining will not yield equivalent assets. The honest claim for hosted-API-dependent builds and stochastic methods without exposed seeds. |

`bit_identical` and `param_identical` REQUIRE `method.code_commit` to
be set. `not_reproducible` does not.

### 5.4 D4 = A — `consent_scope` is a fixed enum

Free-text consent scopes would let every issuer invent their own
vocabulary, defeating the purpose of machine-checkable consent.

The v0.8 fixed enum (defined in the schema's `$defs.consent_scope_enum`)
is:

```text
voice_clone               — synthetic voice generation in the subject's voice
memorial_voice            — voice synthesis after subject's death
voice_recognition         — recognising the subject's voice
text_persona              — text-mode persona / chatbot reflecting the subject
image_avatar              — static image avatars
video_avatar              — animated/video avatars
interactive_chat          — real-time interactive conversation
knowledge_qa              — question-answering grounded in the subject's knowledge
memory_recall             — surfacing the subject's memories on request
agent_action              — taking actions in the world on behalf of the subject
third_party_distribution  — sharing the asset/package with third parties
commercial_use            — using the asset for revenue-generating purposes
research_use              — academic / research use only
derivative_training       — training new models on the asset
public_archival           — long-term public archival (libraries, museums)
license_governed          — input is governed by an external license rather than per-input consent
```

New scopes are added by future spec versions and are additive (existing
packages stay valid). Removing or renaming a scope is a breaking change
and requires a schema-version bump.

The `license_governed` scope is the canonical placeholder for inputs
whose authorisation comes from a license (a public base model, a
licensed dataset) rather than from a personal consent document.
`source_inputs[]` entries of type `base_model` or `dataset` SHOULD use
this scope.

### 5.5 D5 = B — Genesis lives in a separate `genesis/` directory

Two reasons:

1. **Loader speed.** The asset descriptor (in `manifest/manifest.json`)
   stays small so runtimes can scan a `.life` quickly without parsing
   heavy provenance. Genesis files are only opened when the loader
   actually wants the audit detail (withdrawal cascade, license check,
   reproducibility audit).
2. **Tamper detection.** The link between the manifest entry and the
   genesis file is sha256-mediated: tampering with one breaks the
   chain (the per-file hashes recorded in `manifest/manifest.json`
   cover both directories).

`genesis/` joins the existing top-level v0.7 directories (`manifest/`,
`consent/`, `policy/`, `audit/`, `derived/`, `pointers/`,
`encrypted/`); the file layout policy in
[`LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md) MUST be updated by a
companion PR that ships alongside the first `.life` package
publishing genesis.

---

## 6. `consent_scope_checked` semantics

This sub-block is the bridge between consent documents (text) and
genesis records (machine-checkable). Its job is to record that, **at
build time**, a verifier confirmed every scope the build relied on was
covered by the consent evidence.

The block has five required fields:

| Field | Purpose |
|---|---|
| `verified` | Boolean. **Loaders MUST refuse genesis files with `verified: false`** unless an explicit override policy is in effect. |
| `verifier` | Identifier of the tool that performed verification (e.g. `tools/build_life_package.py`). |
| `verifier_version` | Version of the verifier (SemVer or commit fragment). |
| `verified_at` | When verification ran (ISO-8601 UTC). |
| `scopes_used[]` | Every consent scope this build actually relied on. MUST be a subset of the package-level `consent_scope` and of the union of `source_inputs[*].consent_scope`. |

The verifier is responsible for parsing the consent evidence (which
may be a structured `consent.json` or a signed PDF) and confirming
that each entry in `scopes_used` is authorised. v0.8 does NOT
standardise the consent-evidence format; that is the v0.8 binding spec's
companion ([#103]) responsibility for runtime policy and v0.7's
`consent_evidence_ref` for storage.

Example (compliant):

```json
{
  "verified": true,
  "verifier": "tools/build_life_package.py",
  "verifier_version": "0.2.0",
  "verified_at": "2026-04-01T09:30:00Z",
  "scopes_used": ["voice_clone", "interactive_chat", "license_governed"]
}
```

[#103]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/103

---

## 7. Audit-event linkage

Every genesis file MUST point at a corresponding audit event:

- `audit_event_ref` is a `audit/<filename>#L<line>` pointer into the
  package-level audit log (matches the v0.6 descriptor-audit bridge
  convention used elsewhere in the project).
- `audit_event_id` is the stable id of the event itself.

The pointed-to event MUST be of `action: asset_created`, MUST refer
back to `asset_id`, and MUST carry a timestamp consistent with
`compute.finished_at` (the build's wall-clock end).

The audit chain is what makes genesis files trustworthy: a tampered
genesis with no matching audit event is detectable. Loaders SHOULD
validate the cross-reference at load time when the package's
`tier.audit_chain_strength` is `linked` or higher.

---

## 8. Examples

### 8.1 Offline build of a fine-tuned voice clone

```json
{
  "schema_version": "dlrs-life-genesis/0.1",
  "asset_id": "voice-master-v1",
  "asset_kind": "voice_clone",
  "method": {
    "name": "xtts-v2-finetune",
    "version": "1.2.3",
    "config_ref": "configs/voice-master-v1.yaml",
    "code_commit": "108b50c1"
  },
  "source_inputs": [
    {
      "type": "recording",
      "ref": "raw/recording-2025-01-12.wav",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "consent_ref": "consent/recording-2025-01-12.signed.pdf",
      "consent_scope": ["voice_clone", "interactive_chat"]
    },
    {
      "type": "base_model",
      "ref": "https://huggingface.co/coqui/XTTS-v2",
      "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
      "consent_ref": "not_applicable",
      "consent_scope": ["license_governed"],
      "license": "cc-by-nc-4.0",
      "source_url": "https://huggingface.co/coqui/XTTS-v2"
    }
  ],
  "compute": {
    "platform": "local-mac-m2",
    "operator": "alice@example.org",
    "started_at": "2026-04-01T08:00:00Z",
    "finished_at": "2026-04-01T09:30:00Z",
    "hosted_api_used": false,
    "data_left_local": true
  },
  "consent_scope_checked": {
    "verified": true,
    "verifier": "tools/build_life_package.py",
    "verifier_version": "0.2.0",
    "verified_at": "2026-04-01T09:30:00Z",
    "scopes_used": ["voice_clone", "interactive_chat", "license_governed"]
  },
  "audit_event_ref": "audit/events.jsonl#L42",
  "audit_event_id": "01HW91QJTR4ETRBM3DNJK4Y9MA",
  "reproducibility_level": "param_identical",
  "consent_scope": ["voice_clone", "interactive_chat", "memorial_voice"],
  "base_model": {
    "name": "coqui/XTTS-v2",
    "license": "cc-by-nc-4.0",
    "sha256": "1111111111111111111111111111111111111111111111111111111111111111"
  }
}
```

### 8.2 Hosted-API build (declared, not blocked)

```json
{
  "schema_version": "dlrs-life-genesis/0.1",
  "asset_id": "memory-atoms-v3",
  "method": { "name": "hosted-embedding", "version": "1.0.0" },
  "source_inputs": [
    {
      "type": "text",
      "ref": "raw/journal-2025.md",
      "sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
      "consent_ref": "consent/journal-2025.signed.pdf",
      "consent_scope": ["memory_recall", "research_use"]
    }
  ],
  "compute": {
    "platform": "local-linux-cpu",
    "operator": "alice@example.org",
    "started_at": "2026-04-01T11:00:00Z",
    "finished_at": "2026-04-01T11:05:00Z",
    "hosted_api_used": true,
    "data_left_local": false,
    "hosted_api_providers": [
      {
        "name": "openai",
        "endpoint": "https://api.openai.com/v1/embeddings",
        "purpose": "embedding",
        "data_retention_policy_ref": "https://openai.com/policies/api-data-usage-policies"
      }
    ]
  },
  "consent_scope_checked": {
    "verified": true,
    "verifier": "tools/build_life_package.py",
    "verifier_version": "0.2.0",
    "verified_at": "2026-04-01T11:05:00Z",
    "scopes_used": ["memory_recall"]
  },
  "audit_event_ref": "audit/events.jsonl#L57",
  "audit_event_id": "01HW91W5GV5Q8E8H0G11M3D9YZ",
  "reproducibility_level": "not_reproducible",
  "consent_scope": ["memory_recall"]
}
```

---

## 9. What this spec deliberately leaves out

- **Deterministic builds across machines.** Most modern training cannot
  meet that bar. `bit_identical` is offered as an aspirational level
  for pipelines that do meet it, not as a requirement.
- **Machine-readable license validation.** `base_model.license` and
  `source_inputs[].license` are free-form strings. The set of
  acceptable licenses is loader policy, not spec.
- **Temporal restrictions on consent.** `consent_scope` does not model
  "voice_clone allowed from 2025 to 2030"; that lives in the consent
  evidence document and is enforced by the verifier.
- **Per-input audit events.** This spec links the asset birth to an
  audit event; per-input ingestion events are recorded separately
  via the v0.6 descriptor-audit bridge and are not duplicated here.
- **Cross-asset dependencies.** A `derived` source input simply names
  the upstream artefact by path; the full dependency graph is the
  responsibility of the lifecycle spec ([#102]) via
  `cascade_index.json`.

[#102]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/102

---

## 10. Validation

Run the schema sanity tests:

```bash
python tools/test_genesis_schema.py
```

Or as part of the full repository validation:

```bash
python tools/batch_validate.py
```

The genesis test suite ships 33 cases (3 happy-path + 30 negative)
exercising every required field, every enum, every conditional
(`hosted_api_used → providers required`), and every
`additionalProperties: false` boundary.
