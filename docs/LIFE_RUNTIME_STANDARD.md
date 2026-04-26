# `.life` Runtime Protocol Standard

> Status: **Draft**, part of the `.life Archive + Runtime Standard
> (v0.7-vision-shift)` epic ([#79]). This document specifies how a
> compatible runtime loads + executes a `.life` archive
> ([`docs/LIFE_FILE_STANDARD.md`](LIFE_FILE_STANDARD.md), schema
> [`schemas/life-package.schema.json`](../schemas/life-package.schema.json))
> to produce an *AI digital life instance*. This epic ships the spec
> only; a reference runtime implementation is **deferred to v0.8+**.

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
- Reference runtime implementation (deferred to v0.8+).

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

- Working runtime reference implementation (deferred to DLRS v0.8+
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
