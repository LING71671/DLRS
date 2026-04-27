# `.life` Runtime Protocol Standard

> Status: **Draft**, part of the `.life Archive + Runtime Standard
> (v0.7-vision-shift)` epic ([#79]). This document specifies how a
> compatible runtime loads + executes a `.life` archive
> ([`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md), schema
> [`schemas/life-package.schema.json`](../schemas/life-package.schema.json))
> to produce an *AI digital life instance*. This epic ships the spec
> only; v0.8-asset-architecture added Part B (5-stage assembly) as
> spec; a reference runtime implementation is **deferred to v0.9+**.

[#79]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/79

---

## 1. Scope

A **compatible `.life` runtime** is any system (chat application,
virtual world server, 3D scene, voice assistant, …) that:

1. Accepts a `.life` archive as input.
2. Mounts it according to the load sequence in §2.
3. Operates an interactive instance under the constraints in §3, §4,
   and §5.
4. Releases all derived state on the conditions in §6.

This document defines the **minimum protocol contract**. A runtime
that does not implement every MUST clause is **not** compatible and
SHOULD NOT advertise itself as a `.life` runtime.

The spec is **transport-agnostic**: it does not mandate WebSocket /
gRPC / REST. It defines the *semantics* a runtime must implement
regardless of transport.

### Out of scope

- Choice of LLM, embedding model, ASR model, TTS model, avatar
  renderer.
- UI design, graphics pipeline, voice cloning quality.
- Data residency / sovereignty rules (those are encoded in the
  `.life` itself via `verification_level`, `withdrawal_endpoint`,
  and the upstream object-storage policy in pointer mode).
- Reference runtime implementation (deferred to v0.9+).

---

## 2. Load sequence

A compatible runtime MUST execute the following steps **in order**
when mounting a `.life`. Any failure aborts the mount; the runtime
MUST NOT fall back to a partial / degraded mount.

### 2.1 Open + structural validation

1. Open the archive (zip).
2. Verify the archive contains a top-level `life-package.json`.
3. Parse `life-package.json` and validate against
   [`schemas/life-package.schema.json`](../schemas/life-package.schema.json).
   Reject on any schema violation.

### 2.2 Time-bound + identity check

1. Reject if the current wall-clock time is **after** `expires_at`.
2. Reject if `runtime_compatibility[]` lists any interface this
   runtime does not implement. (Partial implementation is forbidden;
   a runtime either fully implements an interface or it does not
   declare it.)
3. Verify `package_id` has not been previously revoked (consult the
   runtime's revocation cache; see §4.3).

### 2.3 Inventory integrity

1. Iterate every entry in `life-package.json::contents[]`. For each
   entry:
   - Verify the path exists in the zip.
   - Verify the decompressed sha256 matches.
   - Verify the decompressed size matches.
2. Reject on any mismatch.
3. Ensure no zip entry exists that is **not** listed in `contents[]`
   (other than `life-package.json` itself). Such an entry indicates
   tampering or build-tool misuse; reject.

### 2.4 Audit chain verification

1. Read `audit/events.jsonl` line by line.
2. Verify each line's `prev_hash` chains correctly with the previous
   line (see v0.4 audit hash chain semantics).
3. Verify `life-package.json::audit_event_ref` points to a valid
   `package_emitted` event whose payload references this
   `package_id`.
4. Reject on any chain break.

### 2.5 Consent + withdrawal pre-flight

1. Resolve `consent_evidence_ref` (path inside `.life` or external
   URI). The runtime MUST NOT mount if it cannot read the consent
   document.
2. Make an initial poll of `withdrawal_endpoint`:
   - **Online runtimes**: HTTP GET. Receiving any 4xx / 5xx /
     network failure aborts the mount.
   - **Offline-explicit runtimes**: only allowed if the issuer
     pre-authorised offline operation in the consent document AND
     the runtime persists a withdrawal-poll log it can later
     synchronise.
3. The response body of a successful poll MUST be parsed; if it
   indicates `status: "withdrawn"` the runtime MUST refuse to mount.

### 2.6 Mode-specific asset handling

Pointer mode (`mode == "pointer"`):

1. For each `pointers/*.pointer.json`, verify the runtime can resolve
   the `upstream_uri` scheme (e.g. `s3://`, `https://`).
2. Optionally pre-fetch + verify upstream sha256.
3. Refuse to mount if any pointer scheme is unsupported.

Encrypted mode (`mode == "encrypted"`):

1. For each entry in `encryption.recipients[]`, attempt to retrieve
   the unwrapped data-encryption key from the runtime's KMS using
   `kid`. The runtime MUST stop at the first successful unwrap;
   `.life` does not specify a multi-key authorisation policy.
2. For each entry in `encryption.assets[]`:
   - Decrypt `blob_path` using the unwrapped key + `nonce` +
     `auth_tag`.
   - Verify `plaintext_sha256` of the decrypted bytes.
3. Refuse to mount if any decrypt or verify fails.

### 2.7 Personality + memory load

1. Load `manifest.json` (DLRS v0.6 record manifest subset).
2. Load `derived/memory_atoms/*.atoms.jsonl` (if present).
3. Load `derived/knowledge_graph/*.{nodes,edges}.jsonl` (if
   present).
4. Apply `policy/hosted_api.json` opt-in policy (if present;
   default-deny per v0.6).

### 2.8 Bind runtime obligations

The runtime MUST register the following before serving any
interactive turn:

- `ai_disclosure` enforcement hook (every output is tagged at the
  declared level).
- `forbidden_uses[]` refusal hook (every prompt is checked).
- Withdrawal poller (re-poll `withdrawal_endpoint` at least every
  24h; see §4.3).
- Audit-event emitter (every session start, turn, withdrawal poll,
  and termination is recorded; see §5).

After §2.8 succeeds, the runtime emits a `session_started` audit
event referencing `package_id` and may begin serving turns.

---

## 3. Mount semantics

### 3.1 Single-package, single-instance

A runtime MUST treat each mounted `.life` as a single, isolated
instance. Two simultaneous mounts of the same `.life` (same
`package_id`) MUST either:

- Operate as fully independent sessions with no shared mutable
  state, OR
- Refuse the second mount with an explicit `package_already_active`
  error.

Mixing memories across two mounted `.life` files (e.g., merging
memory atoms from two different humans into a single instance) is
**forbidden**. If a runtime supports multi-character ensembles, each
character MUST be a separate mount with a separate session.

### 3.2 Read-only by default

The runtime MUST treat the mounted `.life` as **read-only**. New
memories created during a session (e.g., conversation transcripts,
retrieval results) MUST be stored in *runtime-side* state, not
written back into the `.life`. Producing an updated `.life` is the
authoring side's responsibility (DLRS Git repo + `.life` builder),
not the runtime's.

### 3.3 No raw-asset extraction

The runtime MUST NOT expose raw assets from the `.life` to end
users via copy-out APIs. Audio, video, image, and embedding bytes
MAY be used internally for inference but MUST NOT be downloadable
from the runtime as files except where the consent document
explicitly authorises export.

---

## 4. Runtime obligations

### 4.1 AI disclosure

Every output the runtime produces MUST carry a disclosure consistent
with `life-package.json::ai_disclosure`:

- `visible_label_required` — every textual output prefixed (or
  postfixed, or otherwise visibly labelled) with an indication that
  the speaker is an **AI digital life instance** representing
  `<identifier>`. For voice / video output, the visible label is
  rendered on screen or spoken at session start AND at any topic
  shift declared by the runtime.
- `watermark_required` — visible label PLUS a machine-readable
  watermark (text: zero-width markers; audio: spread-spectrum
  watermark; image / video: spatial watermark).
- `metadata_only_with_consent` — only valid when the consent
  document explicitly authorises invisible-only disclosure for the
  specific consumer (e.g., a research evaluation). Default minimum
  is `visible_label_required`.

The runtime MUST refuse any operator override that lowers the
disclosure level below what the package declared.

### 4.2 Forbidden uses

For every user prompt and every generated output, the runtime MUST
check `forbidden_uses[]` and refuse to produce matching content. The
match MAY be implemented as the runtime's existing safety classifier,
but the *trigger list* is non-negotiably the union of:

- The runtime's baseline safety policy.
- `life-package.json::forbidden_uses[]`.

Refused turns MUST be logged as audit events (see §5) with the
matching `forbidden_uses[]` token recorded.

### 4.3 Withdrawal polling + revocation

The runtime MUST poll `withdrawal_endpoint`:

- At session start (already done in §2.5).
- At least every **24 hours** during long-running sessions.
- Immediately after any consent-relevant operator action (e.g.,
  changing the disclosure level, adding a recipient).

A successful poll returning `status: "withdrawn"` triggers the
withdrawal-on-instance flow:

1. Complete the current turn (do not interrupt mid-utterance).
2. Emit a `session_withdrawn` audit event.
3. Terminate the session.
4. Add `package_id` to the runtime's revocation cache so future
   mounts are rejected immediately.
5. Wipe in-memory state derived from the `.life`. Persisted runtime
   state (e.g., conversation transcripts) MAY be retained per the
   runtime's own retention policy, BUT MUST be marked as derived
   from a withdrawn package.

A network-unreachable `withdrawal_endpoint` during periodic polling
MUST cause the runtime to refuse new turns within a runtime-defined
grace window (recommended ≤24h after the last successful poll) and
terminate the session at the end of that window.

### 4.4 Identity-impersonation safeguards

The runtime MUST NOT:

- Claim the instance **is** the underlying human (e.g., "I am
  Alice").
- Claim that interacting with the instance is equivalent to
  interacting with the human.
- Forge first-person statements about real-world events the human
  did not consent to having narrated.

The runtime MUST:

- Always frame the instance as **an AI digital life instance**.
- Honour any `forbidden_uses[]` entry such as
  `impersonation_for_fraud`, `political_endorsement`, etc.

---

## 5. Audit emission

The runtime MUST emit audit events to its own audit log (separate
from the `.life`'s embedded `audit/events.jsonl`, which is
read-only). The runtime audit log SHOULD use the same hash-chain
format as the v0.4 emitter
([`tools/emit_audit_event.py`](../tools/emit_audit_event.py)).

Required event types:

| event_type | When |
|---|---|
| `session_started` | After §2.8 success. |
| `session_turn` | Every user-prompt → instance-response cycle. |
| `withdrawal_poll` | Every poll of `withdrawal_endpoint`. |
| `session_withdrawn` | On withdrawal-on-instance flow. |
| `session_terminated` | On any termination (timeout, expires_at hit, operator stop, withdrawal). |
| `forbidden_use_refused` | When a turn is refused under §4.2. |
| `disclosure_warning_emitted` | When the runtime applied the §4.1 disclosure (sampled / aggregated, not every output). |

These event types are runtime-side and **do not** need to be added
to the DLRS `audit/events.jsonl::event_type` enum (which governs
authoring-side events).

---

## 6. Termination

A runtime MUST terminate a session and release all in-memory state
on any of the following:

1. `expires_at` reached.
2. `package_id` revoked (withdrawal received, manual operator
   revoke, or upstream `withdrawal_endpoint` reports
   `status: "withdrawn"`).
3. Inventory integrity degradation detected mid-session (e.g.,
   pointer-mode upstream returned a different sha256 on a
   subsequent fetch).
4. Audit-log emission failure persistent beyond a runtime-defined
   tolerance (a runtime that cannot record audit events MUST NOT
   continue serving).
5. Operator stop.

After termination:

- In-memory state derived from the `.life` MUST be released.
- The runtime MUST emit `session_terminated`.
- Persisted state (transcripts, retrieval traces) MAY be retained
  per the runtime's own retention policy AND any explicit terms in
  the consent document.

---

## 7. Forbidden runtime behaviours

A `.life`-compatible runtime MUST NOT:

- Mount a `.life` whose `expires_at` has passed.
- Mount a `.life` whose schema validation failed.
- Mount a `.life` whose audit chain is broken.
- Mount a `.life` whose pointer scheme is unsupported (pointer
  mode) or whose decryption fails (encrypted mode).
- Override `ai_disclosure` to a lower level than declared in the
  package.
- Override `forbidden_uses[]` to be more permissive than declared.
- Skip withdrawal polling.
- Persist unwrapped data-encryption keys to disk in plaintext.
- Combine memories from two mounted `.life` files into a single
  instance.
- Claim the instance **is** the underlying human.

A runtime that violates any of the above is non-compliant and SHOULD
NOT advertise itself as `.life`-compatible.

---

## 8. Conformance + interoperability

Compatible runtimes SHOULD declare conformance via:

- Documenting which `runtime_compatibility[]` interface tokens they
  implement (minimum `dlrs-runtime-v0`).
- Publishing the version of this spec they implement (e.g.
  `life-runtime-v0.1`).
- (Future, deferred to `life-runtime v0.2`) Passing an interop
  conformance suite shipped with the spec.

Two distinct runtimes implementing the same `runtime_compatibility[]`
declarations SHOULD produce comparable instances from the same
`.life`, but byte-identical reproduction is **not** required and is
explicitly out of scope (different LLMs / TTS engines will produce
different outputs).

---

## 9. Ethical positioning (mandatory)

This section is intentionally identical (modulo wording for runtime
context) to `LIFE_FILE_STANDARD.md` §7 and the README first-screen.
It is the non-negotiable framing of `.life` for runtime operators.

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

### Runtime hard rules (all MUST be enforced)

1. Tag every output with the `ai_disclosure` label declared in
   `life-package.json` (§4.1).
2. Honour `forbidden_uses[]` — refuse to generate matching content
   (§4.2).
3. Re-poll `withdrawal_endpoint` at session start AND at least every
   24h thereafter (§4.3).
4. Refuse to mount after `expires_at` (§2.2).
5. Never claim the instance **is** the person (§4.4).

A runtime that does not enforce all five is **not** compatible with
`.life` and SHOULD NOT advertise itself as such.

---

## 10. Reference: cross-document map

| Concern | Document |
|---|---|
| Runtime protocol (this doc) | `docs/LIFE_RUNTIME_STANDARD.md` |
| File format spec | `docs/LIFE_FILE_STANDARD.md` |
| JSON Schema | `schemas/life-package.schema.json` |
| Minimal example builder | `examples/minimal-life-package/` (#83) |
| Repository status / gaps | `docs/IMPLEMENTATION_STATUS.md`, `docs/GAP_ANALYSIS.md` (#87) |
| Roadmap (independent runtime track) | `ROADMAP.md` (#86) |

---

## 11. Non-goals (deferred)

- Working runtime reference implementation (deferred to DLRS v0.9+
  in this repo, OR an out-of-tree implementation by a downstream
  project).
- Specific transport protocol (WebSocket / gRPC / REST) — runtime is
  free to choose.
- Specific LLM / TTS / avatar choice.
- Multi-`.life` ensemble protocol (each `.life` is a separate
  instance in v0.1).
- Federated revocation registry (deferred to `life-runtime v0.2`,
  paired with `life-format v0.3`).
- Interop conformance test suite (deferred to `life-runtime v0.2`).
- Cryptographic signature verification of `signature_ref` (waits on
  `life-format v0.2`).

---

# Part B — v0.8 normative additions (Topic 4)

> Status: **normative** for any runtime claiming `life-runtime ≥ 0.8`
> conformance. v0.7 runtimes MAY ignore Part B. The eight-step load
> sequence in §2 remains correct: Part B does not contradict it,
> rather it imposes a richer, named, five-stage discipline on top of
> it and adds three new normative concepts (Provider Registry,
> sandboxing tiers, bootstrap) that were not specified in v0.7.
>
> Closes sub-issue [#105](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105) of epic
> [#106](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106).
>
> Cross-references:
>
> - Architecture overview: [`docs/LIFE_ASSET_ARCHITECTURE.md`](LIFE_ASSET_ARCHITECTURE.md) §6
> - Binding spec: [`docs/LIFE_BINDING_SPEC.md`](LIFE_BINDING_SPEC.md)
> - Tier spec: [`docs/LIFE_TIER_SPEC.md`](LIFE_TIER_SPEC.md)
> - Lifecycle spec: [`docs/LIFE_LIFECYCLE_SPEC.md`](LIFE_LIFECYCLE_SPEC.md)
> - Genesis spec: [`docs/LIFE_GENESIS_SPEC.md`](LIFE_GENESIS_SPEC.md)

## B.1 Five-stage assembly pipeline

The v0.7 load sequence (§2) is grouped into five named stages.
Loaders MUST execute them in order; any failure aborts assembly,
emits an audit event, and surfaces a structured rejection reason.

| Stage | v0.7 §-mapping | New normative additions in v0.8 |
|---|---|---|
| **1. Verify** | §2.1 + §2.2 + §2.3 + §2.4 + §2.5 | Lifecycle-state gate (`active` / `superseded` / `frozen+memorial` / `withdrawn`); withdrawal endpoint pre-flight; audit-chain hash-link integrity. |
| **2. Resolve** | (new) | Read `binding/runtime_binding.json`; map each capability to a Provider via the Provider Registry (B.2); apply tier-aware fallback (B.3). |
| **3. Assemble** | §2.6 + §2.7 + §2.8 | Instantiate Providers in their declared sandboxing class (B.4); inject `hard_constraints` + `surface.ui_hints.disclosure_label`; emit `capability_bound` audit event per capability. |
| **4. Run** | §3 + §4 (existing) | All v0.7 obligations remain. v0.8 adds: `forbidden_uses` MUST be applied via the same key namespace as `binding.hard_constraints` (hybrid: ~30 core keys + `x-` extensions, fail-close on unknown — see binding spec §7). |
| **5. Guard** | §4.3 + §5 + §6 | Withdrawal watcher (≥ every 24 h); lifecycle watcher (`superseded` / `frozen` / `withdrawn` transitions); expiry watcher; audit emitter. |

### B.1.1 Stage gating (decision **D6=fail-close**)

If any stage fails, loaders MUST:

1. Emit an audit event of type `assembly_aborted` with a `stage`
   field (`verify | resolve | assemble | run | guard`) and a
   structured `reason`.
2. Tear down any partially constructed Provider state.
3. Surface a localised rejection reason to the user (no opaque
   "Failed to load" messages).
4. NOT silently fall back to a degraded mount.

This generalises the existing §2 hard-fail rule across the new
named stages.

## B.2 Provider Registry

A **Provider** is the v0.8 unit of capability execution. Each
Provider implements one or more capabilities declared in
`binding.capabilities` (e.g. `voice_synthesis`, `memory_recall`).

Loaders MUST maintain a **Provider Registry** with at least the
following operations:

- `list_providers(capability) -> [ProviderRef]` — enumerate every
  Provider known to the runtime that exposes the given capability,
  in deterministic priority order.
- `resolve(capability, engine_compatibility[]) -> ProviderRef` —
  walk `engine_compatibility[]` (issuer-declared, ordered) and
  return the first Provider whose `(name, version)` satisfies the
  entry's `version_range` and `strict` flag (see binding spec §5.2).
- `metadata(ProviderRef) -> ProviderMetadata` — return at least the
  Provider's `(name, version, sandbox_class)` so Stage 3 (Assemble)
  can pick the correct sandbox.

The registry's storage shape is implementation-defined. Conformant
implementations are encouraged to expose it via a config file
(`~/.config/dlrs/providers.json` or equivalent) plus a `lifectl
provider list` CLI for inspection.

### B.2.1 The `LifeCapabilityProvider` interface

Every Provider MUST satisfy the following abstract interface
(language-agnostic; the names below are normative; signatures are
illustrative):

```
LifeCapabilityProvider:
  capability_name() -> string                        # e.g. "voice_synthesis"
  provider_name()    -> string                        # e.g. "xtts-v2"
  provider_version() -> semver
  sandbox_class()    -> "built_in" | "user_installed" | "bundled_in_life"

  # Lifecycle (called by Stage 3 Assemble)
  initialize(asset_paths: [path], params: dict, hard_constraints: dict) -> void
  teardown() -> void

  # Hot path (called by Stage 4 Run; per turn / per call)
  invoke(input: dict) -> dict
```

Loaders MUST call `initialize` exactly once per mount, after
sandbox setup; MUST call `teardown` exactly once on unmount or
withdrawal; and MUST treat any exception from `invoke` as a
recoverable per-turn error (logged, audited, no automatic
unmount).

## B.3 Tier-aware resolution

Loaders SHOULD use the package's `tier` block (defined by
[`docs/LIFE_TIER_SPEC.md`](LIFE_TIER_SPEC.md)) when more than one
Provider matches an `engine_compatibility[]` entry:

| Tier band (level) | RECOMMENDED Provider preference |
|---|---|
| I–IV (low) | Lighter / offline / lower-fidelity Providers; preserve playability over fidelity. |
| V–VIII (mid) | Whatever the issuer's first `engine_compatibility[]` entry resolves to; no special bias. |
| IX–XII (high) | Higher-fidelity Providers; for capabilities permitted by `hosted_api_preference` (see B.5), MAY prefer hosted Providers. |

This is a SHOULD, not a MUST: loaders are free to ignore the tier
band if their environment dictates a fixed Provider choice (e.g. an
embedded runtime with one TTS engine only).

Loaders MUST honour `capability_binding.tier_floor` (binding spec
§5.1) when present: if the package's `tier.level` is below the
floor, the loader SHOULD warn the user before binding; whether to
proceed is a user / policy decision, not a hard refusal.

## B.4 Sandboxing classes (decision **D1=C, graded sandbox**)

Every Provider declares a sandbox class via `sandbox_class()`. The
runtime MUST enforce the following minimum boundary per class:

| Class | Trust assumption | Minimum boundary |
|---|---|---|
| `built_in` | Ships with the runtime; signed by the runtime vendor. | Same OS process as the runtime; no extra sandbox required. |
| `user_installed` | Installed by the user via OS package manager or `lifectl`. The user accepts that this code runs on their machine. | Runtime MUST run the Provider in a separate OS process with IPC; a stricter sandbox (firejail / nsjail / seccomp / wasm) is RECOMMENDED but not required. |
| `bundled_in_life` | Vendored inside the `.life` zip itself; untrusted. | **REJECTED at v0.8** (decision **D2=B**, see B.4.1). Not loadable until v1.0+ when a whitelisted-issuer scheme exists (decision **D2=C**). |

Loaders MUST refuse to bind a capability whose chosen Provider has
`sandbox_class() == "bundled_in_life"` until the v1.0+ whitelist
scheme lands. The binding schema rejects
`engine_kind: bundled_in_life` statically (binding spec §5.2), but
runtimes MUST also enforce this at Stage 2 (Resolve) as defence in
depth.

### B.4.1 Why `bundled_in_life` is forbidden in v0.8 (D2=B)

Letting an arbitrary `.life` ship arbitrary code is equivalent to
running an unsigned binary downloaded from the internet. The v0.8
ecosystem has no trust anchor that could authorise a third-party
`.life` to execute its own code; until issuer-whitelisting and
revocation are spec'd (target: v1.0+), `bundled_in_life` Providers
are unconditionally refused. This is intentional and is **not** a
schema bug.

## B.5 Hosted-API AND-gate (decision **D5=mixed**)

A hosted-API call MAY fire **only if** both halves of the AND-gate
say "allow":

```
ALLOW HOSTED CALL  ⇔  binding.hosted_api_preference.allowed == true
                       AND policy/hosted_api.json permits this provider/capability
```

Either rejecting is sufficient. The default for a missing
`hosted_api_preference` block is `allowed: false` (binding spec §9).

The package's tier MAY influence the default user-side preference
in a runtime's UI (e.g. "this is a Tier IX package — would you like
to use hosted higher-fidelity providers? Y/N"), but the underlying
AND-gate is unchanged: the user retains the final veto. There is no
"recommend offline" or "recommend hosted" baked into the spec —
both modes are first-class (decision **D3=mixed**).

## B.6 Bootstrap (decision **D5=C, OS package manager**)

Users acquire a runtime via the host OS's package manager:

```
brew install dlrs-runtime         # macOS
apt  install dlrs-runtime          # Debian / Ubuntu
winget install dlrs-runtime        # Windows
```

The `.life` archive MUST NOT carry a self-extracting bootstrap
stub. Loaders MUST NOT auto-fetch the runtime from a `.life`. This
preserves the trust boundary: the runtime is something the user
explicitly installed, not something a `.life` can install on their
behalf.

When the OS does not have an associated `.life` handler, the OS
fallback (e.g. "find application to open this file") is permitted
to direct the user to `https://dlrs.standard/install` or an
equivalent canonical install page. The `.life` itself is inert
until a runtime is installed.

## B.7 Audit additions (v0.8)

In addition to the v0.7 audit-event vocabulary, conformant runtimes
MUST emit:

| Event type | When | Required fields |
|---|---|---|
| `capability_bound` | Once per capability after Stage 3 Assemble succeeds. | `capability`, `provider_name`, `provider_version`, `sandbox_class`. |
| `assembly_aborted` | Stage failure (B.1.1). | `stage`, `reason`. |
| `withdrawal_poll` (existing v0.7 event, see §5) | Each withdrawal-watcher poll (Stage 5 Guard). v0.8 makes the fields `endpoint` and `result` required. | `endpoint`, `result`. |
| `lifecycle_transition_observed` | Stage 5 Guard observes a `lifecycle_state` transition (`active` → `superseded` / `frozen` / `withdrawn`). | `from_state`, `to_state`, `package_id`. |

Existing v0.7 events (`session_started`, `session_turn`,
`session_withdrawn`, `session_terminated`, `forbidden_use_refused`,
`disclosure_warning_emitted` — see §5) are unchanged.

## B.8 What this update does NOT add

- **Provider sandbox implementation** — runtimes pick their own
  sandbox technology (firejail, nsjail, wasm, etc.) per platform.
  Spec only mandates the boundary.
- **Provider distribution registry** — Providers are distributed
  via OS package managers / `lifectl` repositories; the spec does
  not standardise the registry format itself yet (deferred to
  `life-runtime 0.2`).
- **Runtime cryptographic identity** — Providers do not yet ship
  signatures; trust is anchored on the OS package manager. A
  signed-Provider scheme is deferred to v1.0+ alongside the
  `bundled_in_life` whitelisting work.
- **Failover across runtimes** — if a Provider crashes, the runtime
  MUST treat it as a per-turn error (B.2.1); migrating an active
  mount to a different runtime instance is out of scope.

## B.9 Decisions encoded

| # | Decision | Realised in |
|---|---|---|
| **D1=C** | Graded sandbox (built-in / user-installed / `.life`-bundled) | B.4 |
| **D2=B** | v0.8: no bundled Providers | B.4 + B.4.1 |
| **D2=C** | v1.0+: whitelisted-issuer Providers (deferred) | B.8 |
| **D3=mixed** | Both offline and hosted are first-class | B.5 |
| **D4=C** | Three-field surface shape (`supported`, `preferred`, `minimum_required`) | binding spec §8 |
| **D5=C** | OS package manager bootstrap | B.6 |
| **D6=fail-close** | Stage failure aborts assembly, no degraded mount | B.1.1 |

[#105]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/105
[#106]: https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106
