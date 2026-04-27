# `.life` Archive File Standard

> Status: **Draft**, part of the `.life Archive + Runtime Standard
> (v0.7-vision-shift)` epic ([#79]). Authoritative spec lives in this
> file. The matching JSON Schema is
> [`schemas/life-package.schema.json`](../schemas/life-package.schema.json)
> (see [#82]). The matching runtime protocol is
> [`docs/LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md) (see [#84]).

[#79]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/79
[#82]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/82
[#84]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/84

---

## 1. What `.life` is — and is not

### What `.life` is

A `.life` file is a **portable, signed, time-bounded digital-life
archive package** generated under the consent of the subject (or an
authorized representative). It is the **distribution unit** of the
DLRS standard: one canonical package that any compatible runtime can
load to produce an *AI digital life instance*.

A `.life` package can include:

- **Identity description** (who the package represents, at what
  verification level, who issued it)
- **Authorization evidence** (consent documents or pointers, time
  windows, withdrawal endpoint)
- **Memory structures** (memory atoms, knowledge graph nodes/edges)
- **Personality preferences** (style, tone, forbidden uses, allowed
  use cases)
- **Multimodal asset pointers** (text / audio / image / video — by
  default *pointers*, not raw bytes; see modes below)
- **Model references** (which embedding / ASR / generation models the
  package was built against)
- **Verification level** (`self_attested` / `third_party_verified` /
  `memorial_authorized`)
- **Audit log** (a hash-chained subset of `audit/events.jsonl` from
  the source DLRS record)
- **Withdrawal mechanism** (a URI runtimes MUST poll to honour
  consent withdrawal in real time)

### What `.life` is NOT

`.life` is **not**:

- ❌ A "resurrection" technology. A `.life` instance is not the
  underlying human; it is a representation operating under specified
  constraints.
- ❌ A claim that the AI instance equals the person. Compatible
  runtimes MUST always identify the result as an **AI digital life
  instance** (see [`LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md)
  for runtime obligations).
- ❌ A consent-free post-mortem reanimation tool. Memorial-mode
  `.life` files require an authorized representative + an active
  withdrawal endpoint.
- ❌ A working runtime — this epic ships specs + schema + an example
  builder. Runtime reference implementations are deferred to v0.8+.
- ❌ A container for raw biometric data in pointer mode. By default
  raw audio / video / image stays in upstream object storage; the
  `.life` only ships *pointers*.

---

## 2. Package layout

A `.life` file is a **zip archive** (suffix `.life`, MIME
`application/vnd.dlrs.life+zip`) with the following top-level layout:

```text
mylife.life (zip archive)
├── life-package.json         REQUIRED — top descriptor (this spec)
├── manifest.json             REQUIRED — DLRS v0.6 record manifest (subset OK)
├── consent/                  REQUIRED — consent evidence or pointer
│   └── consent.md
├── policy/
│   └── hosted_api.json       OPTIONAL — v0.6 hosted-API opt-in policy
├── audit/
│   └── events.jsonl          REQUIRED — hash-chained audit subset
├── derived/                  OPTIONAL — pipeline outputs + descriptors
│   ├── memory_atoms/*.atoms.jsonl
│   ├── knowledge_graph/*.{nodes,edges}.jsonl
│   └── ...
├── pointers/                 REQUIRED in pointer mode
│   └── *.pointer.json
└── encrypted/                REQUIRED in encrypted mode
    └── *.bin (sealed blobs)
```

### Required entries (every `.life`)

| Path | Notes |
|---|---|
| `life-package.json` | Top descriptor; see §4. |
| `manifest.json` | A DLRS v0.6 manifest, optionally a subset of the source record's manifest (only the fields needed for this distribution). |
| `consent/` | At least one consent document or pointer. The exact path is referenced from `life-package.json::consent_evidence_ref`. |
| `audit/events.jsonl` | Hash-chained audit subset. The head hash MUST match the line referenced by `life-package.json::audit_event_ref`. |

### Mode-conditional entries

- **`mode == "pointer"`**: `pointers/` directory MUST exist with at
  least one `*.pointer.json` for any non-text asset referenced by
  `manifest.json`. `encrypted/` MUST NOT exist.
- **`mode == "encrypted"`**: `encrypted/` directory MUST exist with
  one sealed blob per asset. `pointers/` MUST NOT exist. The
  `life-package.json::encryption` block MUST be present.

### Forbidden entries

- Raw biometric data in pointer mode (audio / video / images that
  bypass `pointers/`).
- Any file path outside the eight top-level entries above.
- Any path containing `..` or absolute paths.
- Any symlinks (zip archive MUST be flat / regular files only).

---

## 3. The two modes

| Mode | When to use | Asset access | Encryption | Default |
|---|---|---|---|---|
| **`pointer`** | Runtime is online + has access to upstream object storage and model registry. Privacy-preserving: raw assets stay encrypted at rest in upstream storage. | Pointers only — `*.pointer.json` files inside `pointers/` describe the upstream URI, sha256, size, and content type. | None at package level. Upstream storage is responsible for encryption-at-rest. | ✅ Yes |
| **`encrypted`** | Runtime needs to operate **without** upstream access (offline, federated, or sovereign deployment). Off-grid full pack. | Sealed blobs inside `encrypted/`. | AEAD (AES-256-GCM minimum, ChaCha20-Poly1305 acceptable). Keys are distributed out-of-band via KMS, wrapped per recipient. The package itself does NOT contain unwrapped keys. | ❌ Opt-in |

A `.life` MUST declare exactly one mode in
`life-package.json::mode`. Mixed-mode packages (some pointers + some
encrypted blobs) are **not** permitted in `.life` v0.1; deferred to
a later spec revision.

### Pointer-mode pointer-file format

A pointer file under `pointers/` is JSON:

```json
{
  "kind": "audio",
  "upstream_uri": "s3://example-dlrs-bucket/voice/master.wav",
  "sha256": "sha256:7b9e9f3a...",
  "size": 18483712,
  "content_type": "audio/wav",
  "encryption_at_rest": "aws-kms://key-id/12345"
}
```

Runtimes resolve `upstream_uri` according to their compatibility
declaration; runtimes that cannot resolve a particular scheme MUST
refuse to mount the package rather than silently degrade.

### Encrypted-mode blob format

Each blob under `encrypted/` is the AEAD ciphertext of the
corresponding asset. The mapping from logical asset → blob path +
nonce + tag is recorded inside `life-package.json::encryption.assets`
(see §4). Blob filenames are opaque (e.g., `<sha256>.bin`); they are
**not** the asset's hash, they are the *plaintext sha256* of the
asset, used as a stable identifier.

---

## 4. `life-package.json` field reference

`life-package.json` MUST validate against
[`schemas/life-package.schema.json`](../schemas/life-package.schema.json)
(JSON Schema Draft 2020-12, `additionalProperties: false`).

| Field | Required | Type | Notes |
|---|---|---|---|
| `schema_version` | yes | const `"0.1.0"` | `.life` format semver, **independent** of DLRS repo version. |
| `package_id` | yes | string (ULID) | Unique per package emission. |
| `mode` | yes | enum `"pointer"`, `"encrypted"` | See §3. |
| `record_id` | yes | string | Points back to the source DLRS record (`humans/<id>`). |
| `created_at` | yes | string (RFC 3339) | When the package was built. |
| `expires_at` | yes | string (RFC 3339) | Runtimes MUST refuse to mount after this. |
| `issued_by` | yes | object | `{role, identifier, signature_ref}` — see below. |
| `consent_evidence_ref` | yes | string | Path inside `.life` (e.g., `consent/consent.md`) or external URI. |
| `verification_level` | yes (DEPRECATED v0.8) | enum | `"self_attested"`, `"third_party_verified"`, `"memorial_authorized"`. Retained required for v0.1 back-compat; new packages SHOULD carry a `tier` block and new consumers SHOULD read `tier.dimensions.identity_verification` instead. Mapping table in `docs/LIFE_TIER_SPEC.md` §6. |
| `tier` | no (v0.8+) | object | v0.8 multi-dimensional credit rating. Auto-computed at build time; see `docs/LIFE_TIER_SPEC.md` for the full normative definition. Absent in v0.7 packages; present in v0.8+ packages built with `tools/build_life_package.py` ≥ 0.2.0. |
| `withdrawal_endpoint` | yes | string (URI) | Runtimes MUST poll this at session start + at least every 24h. |
| `runtime_compatibility` | yes | array of strings | Required runtime interfaces (e.g., `["dlrs-runtime-v0", "openai-chat-tool", "vrm-1.0"]`). |
| `ai_disclosure` | yes | enum | Mirrors v0.4 `ai_disclosure`. Minimum is `visible_label_required`. |
| `forbidden_uses` | yes | array of strings | Free-form, but SHOULD include `impersonation_for_fraud`, `political_endorsement`, `explicit_content` where applicable. |
| `audit_event_ref` | yes | string | `audit/events.jsonl#L<n>` — the `package_emitted` event covering this package. |
| `encryption` | conditional | object | Required iff `mode == "encrypted"`. See §3. |
| `contents` | yes | array of object | Inventory `[{path, sha256, size}, ...]` — every regular file in the zip MUST appear exactly once. Used for integrity verification at runtime. |
| `notes` | no | string | Free text, human-readable. |

### `issued_by` shape

```json
{
  "role": "self" | "authorized_representative" | "memorial_executor",
  "identifier": "<opaque human-readable identifier>",
  "signature_ref": "<URI or path inside .life>"
}
```

- `role: "self"` — the subject of the package issued it themselves.
- `role: "authorized_representative"` — a legal representative
  (e.g., guardian, agent under power of attorney).
- `role: "memorial_executor"` — post-mortem only; requires
  `verification_level: "memorial_authorized"` and a valid
  `withdrawal_endpoint`.

`signature_ref` is opaque in `.life` v0.1 (a path or URI). A
cryptographic signature scheme is deferred to v0.2 / v1.0 (see
[ROADMAP.md](../ROADMAP.md) `.life Archive Standard 路线图`).

### `encryption` shape (required when `mode == "encrypted"`)

```json
{
  "algorithm": "AES-256-GCM",
  "key_distribution": "external_kms",
  "recipients": [
    { "kid": "kms://example/key-1", "wrapped_key_ref": "encrypted/wrapped-key-1.bin" }
  ],
  "assets": [
    {
      "logical_path": "voice/master.wav",
      "blob_path": "encrypted/<plaintext_sha256>.bin",
      "plaintext_sha256": "sha256:7b9e9f3a...",
      "nonce": "<base64>",
      "auth_tag": "<base64>"
    }
  ]
}
```

`.life` v0.1 reserves these field names but does not mandate a
specific KMS protocol. Runtimes that do not support
`key_distribution: "external_kms"` MUST refuse to mount.

### `contents` integrity

Every regular file inside the zip — *including* `manifest.json`,
`consent/*`, `audit/events.jsonl`, `derived/**`, `pointers/**`,
`encrypted/**` — MUST be listed exactly once in
`life-package.json::contents` with its sha256 and size. Runtimes
MUST verify each entry at load. `life-package.json` itself is
**excluded** from `contents` (it is the manifest of the manifests).

---

## 5. Authoring workflow (DLRS record → `.life`)

A `.life` builder MUST:

1. Start from a DLRS v0.6 record directory (`humans/<id>/`).
2. Choose subset: which derived assets, which audit-event range,
   which consent docs. Subset selection is the builder's policy and
   is recorded in `manifest.json` if it differs from the source
   record's full manifest.
3. Compute sha256 + size for every file to be packaged.
4. Construct `life-package.json` with `package_id` (fresh ULID),
   `mode`, `created_at`, `expires_at`, `issued_by`,
   `consent_evidence_ref`, `verification_level`,
   `withdrawal_endpoint`, `runtime_compatibility`, `ai_disclosure`,
   `forbidden_uses`, and `contents[]`.
5. Append a `package_emitted` event to the source record's
   `audit/events.jsonl` (using the v0.4 audit emitter; reuse the
   existing hash chain).
6. Copy the audit subset into `<life>/audit/events.jsonl`.
7. Set `audit_event_ref` to `audit/events.jsonl#L<n>` where `n` is
   the line number of the `package_emitted` event inside the
   *bundled* `audit/events.jsonl` (not the source record's).
8. If `mode == "encrypted"`, encrypt assets, write `encrypted/`, fill
   `encryption.assets[]`.
9. If `mode == "pointer"`, copy `*.pointer.json` files into
   `pointers/`. Verify no raw biometric data has leaked into the zip.
10. Compute final zip with deterministic ordering (alphabetical, no
    timestamps that change between builds). Output `<name>.life`.

The `examples/minimal-life-package/build_life.sh` builder
(see [#83]) demonstrates this end-to-end for a pointer-mode package.

[#83]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/83

---

## 6. Versioning

The `.life` file format has its own semver track,
**independent of the DLRS repo version**.

- `life-format v0.1.0` — this spec. Pointer mode + encrypted mode
  framework, ULID `package_id`, RFC 3339 times, opaque
  `signature_ref`. No cryptographic signature scheme.
- `life-format v0.2.0` *(planned)* — cryptographic signature scheme
  (likely C2PA-aligned), conformance suite, `mixed` mode evaluation.
- `life-format v0.3.0` *(planned)* — federated discovery + revocation
  registry.

Schema-only-additive bumps (e.g., new optional fields) are minor
versions. Any breaking change (rename, removed field, tightened
enum) is a major bump. See ROADMAP.

---

## 7. Ethical positioning (mandatory)

This section is intentionally repeated across `LIFE_FILE_STANDARD.md`,
`LIFE_RUNTIME_STANDARD.md`, and the README first-screen. It is the
non-negotiable framing of `.life`.

### `.life` is

- A **consented, revocable, auditable** digital representation.
- A **signed, time-bounded license** to operate an AI instance under
  specified constraints.
- Always identifiable as **AI digital life instance**, never as the
  underlying human.

### `.life` is not

- A "resurrection" technology.
- A claim that the AI instance equals the person.
- A consent-free post-mortem reanimation tool.

### Hard rules carried into the runtime spec

A compatible runtime ([`LIFE_RUNTIME_STANDARD.md`](LIFE_RUNTIME_STANDARD.md))
MUST:

- Tag every output with the `ai_disclosure` label declared in
  `life-package.json` (visible label / watermark / metadata,
  depending on modality).
- Honour `forbidden_uses[]` — refuse to generate matching content.
- Re-poll `withdrawal_endpoint` at session start and at least every
  24h thereafter. On withdrawal, complete the current turn and
  terminate.
- Refuse to mount after `expires_at`.
- Never claim the instance **is** the person.

A runtime that does not enforce these rules is **not** compatible
with `.life` and SHOULD NOT advertise itself as such.

---

## 8. Reference: cross-document map

| Concern | Document |
|---|---|
| File format spec (this doc) | `docs/LIFE_FILE_STANDARD.md` |
| JSON Schema | `schemas/life-package.schema.json` ([#82]) |
| Minimal example builder | `examples/minimal-life-package/` ([#83]) |
| Runtime protocol | `docs/LIFE_RUNTIME_STANDARD.md` ([#84]) |
| Repository status / gaps | `docs/IMPLEMENTATION_STATUS.md`, `docs/GAP_ANALYSIS.md` ([#87]) |
| Roadmap (independent `.life` track) | `ROADMAP.md` ([#86]) |

[#86]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/86
[#87]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/87

---

## 9. Non-goals (deferred)

- Working runtime reference implementation (deferred to v0.8+ DLRS
  repo versions).
- Cryptographic signature scheme for `signature_ref` (deferred to
  `life-format v0.2`, likely C2PA).
- Federated `.life` registry / discovery / revocation
  (`life-format v0.3`).
- Multi-recipient encrypted-mode key wrapping protocol (declared in
  schema, no specified protocol in v0.1).
- Inter-runtime portability conformance suite (deferred to
  `life-format v0.2`).
- `mixed` mode (some pointers + some encrypted blobs in the same
  package) — out of scope for v0.1.
