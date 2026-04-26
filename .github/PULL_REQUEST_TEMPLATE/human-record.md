<!--
Use this template when contributing a NEW human record archive under humans/.

Title format: "[record] dlrs_<id> <display_slug>"

Open this template via the URL parameter:
?template=human-record.md
-->

# Human-record contribution

## 0. Archive type

- [ ] `self`
- [ ] `authorized_agent`
- [ ] `estate_authorized`
- [ ] `public_data_only`
- [ ] `research_consented`

## 1. Consent checklist

- [ ] `consent/consent_statement.<lang>.md` is signed and dated.
- [ ] A consent video pointer (`consent/consent_video.pointer.json`) is included if the record uses voice / face / biometric data.
- [ ] `consent/id_verification.pointer.json` references the verification material (NEVER the raw ID).
- [ ] The signer has legal authority to provide consent (subject / guardian / executor).
- [ ] If voice / avatar / biometric scopes are enabled, **separate biometric consent** is documented and `manifest.consent.separate_biometric_consent=true`.
- [ ] For minors: `subject.is_minor=true`, guardian consent documented, visibility ≠ public.
- [ ] For deceased subjects: `subject.status="deceased"`, `inheritance_policy.default_action_on_death` is set, `policies/deceased-persons.md` is followed.

## 2. Sensitive-materials checklist

- [ ] No raw audio, video, image, biometric, or ID files are committed (run `python tools/check_sensitive_files.py`).
- [ ] All sensitive assets use `*.pointer.json` files in `artifacts/raw_pointers/<type>/`.
- [ ] Every pointer carries a valid `checksum` (e.g. `sha256:...`) and `size_bytes`.
- [ ] Storage URIs follow the [Object Storage Pointer Specification](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/docs/OBJECT_STORAGE_POINTERS.md).
- [ ] `sensitivity` levels match the actual content (S3+ for biometric, S4 for ID).
- [ ] Pointer `media_metadata` meets the minimums in [`docs/COLLECTION_STANDARD.md`](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/docs/COLLECTION_STANDARD.md).

## 3. Public-registry checklist

- [ ] `public_profile.json` is complete and accurate.
- [ ] `ai_disclosure` is present and clear that interactions are AI-mediated.
- [ ] `allowed_public_interactions` reflects what the subject actually agreed to.
- [ ] Privacy preferences (`rights.allow_*`) match the consent statement.
- [ ] `rights.allow_public_listing` is set deliberately.
- [ ] `display_name` does NOT include private legal names unless explicitly approved.

## 4. Withdrawal endpoint checklist

- [ ] `manifest.consent.withdrawal_endpoint` is set and reachable (URL or `mailto:`).
- [ ] The withdrawal channel is documented in the archive's local `README.md`.
- [ ] Subject (or representative) knows how to invoke withdrawal.

## 5. Validation

Run locally before requesting review:

```bash
python -m pip install -r tools/requirements.txt
python tools/check_sensitive_files.py
python tools/validate_repo.py
python tools/validate_media.py
python tools/test_registry.py
python tools/build_registry.py
```

- [ ] All commands above exit 0.
- [ ] CI (`.github/workflows/validate.yml`) is green for this PR.

## 6. Reviewer notes

> Reviewers: leave verification notes here. If anything is missing, request changes rather than merging.

| Item                                | Status (✓/✗) | Reviewer notes |
| ----------------------------------- | ----------- | --------------- |
| Consent statement valid             |             |                 |
| Pointer files conform to spec       |             |                 |
| Sensitivity levels appropriate      |             |                 |
| Withdrawal endpoint reachable       |             |                 |
| `public_profile.json` safe          |             |                 |
| Risk level assignment               |             |                 |

## 7. Description (free text)

Please describe the record's intended use, any unusual rights situation, and anything else reviewers should know.
