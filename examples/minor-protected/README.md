# Example: minor-protected

A fictional DLRS record for a data subject under the age of majority. The point of
this example is **what should be excluded from the public registry**.

## Why this is a "negative" example

Under PIPL §31 (China), GDPR Art. 8 (EU), and parallel rules in most jurisdictions,
processing personal information about minors requires guardian consent and stricter
default privacy. DLRS encodes this with the `subject.is_minor = true` flag.

When `is_minor = true`:

- `tools/build_registry.py` filters the record out of `registry/humans.index.jsonl`
  even if `visibility = public_*` were set (which it never should be for minors).
- The reviewer flow (`docs/COMPLIANCE_CHECKLIST.md` §4) blocks public approval.
- `consent.guardian_consent` MUST be `true` and `consent/guardian_consent.pointer.json`
  is the supporting evidence.

## What to look at

- `manifest.json`: `subject.is_minor = true`, `visibility = private`,
  `review.status = approved_private`. The record carries `verified_consent_badge`
  but still does not appear in the public registry.
- `public_profile.json`: minimal, AI disclosure clearly states the minor-data
  context.
- `tools/test_registry.py` includes a dedicated test case
  `minor_excluded_even_when_public` that asserts the exclusion logic.

## What this example does NOT do

- It does not contain real biometric data; the storage_uri values are placeholders.
- It does not enable `voice_clone` or `avatar_clone`; both are explicitly `false`
  in `rights.*`.
- It does not include cross-border transfer; `cross_border_transfer_basis = none`.
