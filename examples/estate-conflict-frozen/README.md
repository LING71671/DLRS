# Example: estate-conflict-frozen

A fictional DLRS record for a deceased subject whose archive is under dispute
(typical case: surviving relatives disagree on whether to enable a memorial avatar,
or there is unresolved IP / publicity-rights litigation). The point of this example
is **what 'frozen' looks like in DLRS terms**.

## Why this is a "negative" example

DLRS_ULTIMATE.md §运维治理 prescribes a defensive default for ambiguous estate
situations: freeze the runtime, preserve the data and audit trail, refuse public
exposure, and wait for legal authority before further action. This example encodes
that posture in the manifest.

Concretely:

- `subject.status = deceased`
- `deletion_policy.legal_hold = true`
- `deletion_policy.allow_delete = false` and `allow_export = false`
- `rights.allow_public_listing = false`
- `rights.cross_border_transfer_status = blocked`
- `review.status = blocked`, `risk_level = critical`
- `inheritance_policy.default_action_on_death = memorial_private`

These flags propagate through `tools/build_registry.py` so the record never
appears in the public registry.

## What this example demonstrates

1. The PR / review template forces a reviewer to confirm legal hold before the
   record is set to anything other than `blocked`.
2. The audit events file (`audit/events.jsonl`) is the place to record the
   `inheritance_trigger` and any subsequent `consent_withdrawn` / `take_down`
   events; emit them with `tools/emit_audit_event.py`.
3. The reviewer notes (`review.reviewer_notes_ref`) MUST cite the controlling
   evidence (will, court order, executor authorisation) — `[需律师审阅]`.

## What this example does NOT do

- It does not store any synthetic outputs; runtime is frozen.
- It does not include a `verified_consent_badge`; the original subject can no
  longer give live consent.
- It is not a substitute for legal counsel. Real estate-conflict cases require
  jurisdiction-specific advice.
