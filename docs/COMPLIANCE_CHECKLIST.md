# DLRS Compliance Self-Checklist (PIPL / GDPR / EU AI Act)

> Audience: archive maintainers, contributors filing a `human-record` PR, and
> reviewers signing off on registry inclusion.
>
> Status: **self-check**. This document is not a substitute for legal advice.
> Items flagged `[需律师审阅]` MUST be reviewed by counsel for the relevant
> jurisdiction before the record is set to `visibility: public_*`.

The table below maps each clause of the three primary legal regimes that the
DLRS Ultimate spec relies on (`DLRS_ULTIMATE.md` §合同与责任声明 / §运维治理) to:

- the manifest field that operationalises the obligation,
- the validator that enforces it (where it exists today),
- whether the v0.4 schema makes it a hard machine-checked constraint.

If a row says `Hard schema constraint? = no`, the obligation is still binding;
it just has to be enforced by review (`reviewer_notes_ref`) rather than by CI.

## 中华人民共和国《个人信息保护法》（PIPL）

| Article | Obligation | Manifest field / artefact | Validator | Hard schema constraint? |
|---|---|---|---|---|
| §13 | Lawful basis for processing | `rights.rights_basis[]` | `validate_repo.py` | yes (required, non-empty) |
| §14, §17 | Informed, specific consent | `consent/consent_statement.md` + `consent.consent_version` | `validate_repo.py` | yes (consent.required fields) |
| §15 | Right to withdraw consent | `consent.withdrawal_endpoint` | `validate_repo.py` | yes (minLength 3, required) |
| §28 | Sensitive personal information | `artifacts[].sensitivity` ≥ `S2` for biometric / health data | `validate_repo.py`, `validate_media.py` | yes (enum) |
| §29 | Separate consent for sensitive data | `consent.separate_biometric_consent` | `validate_repo.py` | yes (required) |
| §31 | Minors under 14 | `subject.is_minor` + `consent.guardian_consent`; record MUST NOT enter public registry | `test_registry.py` (case `minor_excluded_from_registry`) | yes (registry filter) |
| §38 | Cross-border transfer legal basis | `rights.cross_border_transfer_basis` | `validate_repo.py` | yes (enum, required) |
| §44 | Right to access / copy | `deletion_policy.allow_export = true` SHOULD be set | reviewer | no — review via PR template |
| §45–47 | Right to deletion | `deletion_policy.allow_delete`, `deletion_policy.withdrawal_effect` | `validate_repo.py` | yes |
| §49 | Death of data subject | `inheritance_policy.default_action_on_death` | `validate_repo.py` | yes (enum) |
| §51 | Logging and audit | `audit.events_log_ref` → `audit/events.jsonl` | `tools/emit_audit_event.py` produces it | partial (field optional in v0.4) |
| §55 | Impact assessment for high-risk processing | `review.risk_level = high` triggers extra review | reviewer | no — `[需律师审阅]` |

## EU GDPR

| Article | Obligation | Manifest field / artefact | Validator | Hard schema constraint? |
|---|---|---|---|---|
| Art. 6 | Lawful basis | `rights.rights_basis[]` | `validate_repo.py` | yes |
| Art. 7 | Demonstrate consent | `consent/signer_signature.json` and `consent/consent_video.pointer.json` | `validate_repo.py` | partial (fields optional) |
| Art. 9 | Special categories of data | `artifacts[].sensitivity` ≥ `S3_BIOMETRIC` | schema enum | yes |
| Art. 13 | Information to data subject | `consent/consent_statement.md` | reviewer | no |
| Art. 15 | Right of access | `deletion_policy.allow_export` | reviewer | no |
| Art. 17 | Right to erasure | `deletion_policy.allow_delete` + `withdrawal_effect` | `validate_repo.py` | yes |
| Art. 20 | Data portability | `export_format_available` (advisory) | reviewer | no |
| Art. 30 | Records of processing activities | `audit.events_log_ref` + `tools/emit_audit_event.py` | `tools/batch_validate.py` | partial |
| Art. 32 | Security of processing | `security.encryption_at_rest`, `security.kms_ref` | `validate_repo.py` | yes (encryption_at_rest required) |
| Art. 35 | DPIA for high-risk processing | `review.risk_level = high` + `[需律师审阅]` | reviewer | no |
| Art. 44 | Cross-border transfer | `rights.cross_border_transfer_basis` ∈ {standard_contract, certification, security_assessment} | `validate_repo.py` | yes |

## EU AI Act (Regulation 2024/1689)

| Article | Obligation | Manifest field / artefact | Validator | Hard schema constraint? |
|---|---|---|---|---|
| §50(1) | Disclosure of synthetic interaction | `public_disclosure.label_text_required` | `validate_repo.py` | yes (required for public_*) |
| §50(2) | Machine-readable marking of AI-generated content | `public_disclosure.watermark_methods[]` and `public_disclosure.c2pa_claim_generator` | reviewer; v0.4 records the *declaration*, v1.0+ enforces the actual mark | partial |
| §50(3) | Disclosure of deep fakes | `public_disclosure.ai_disclosure ∈ {visible_label_and_watermark, c2pa_required}` for any avatar/voice clone | `validate_repo.py` | yes (enum) |
| §50(4) | Right to know an AI system is used | `public_disclosure.label_locales[]` for the audience locale | reviewer | partial |
| Annex IV §2 | Logging and traceability | `audit.events_log_ref` | `tools/emit_audit_event.py` | partial |

## Chinese Generative AI / Deep Synthesis Rules

| Source | Obligation | Manifest field / artefact | Validator | Hard schema constraint? |
|---|---|---|---|---|
| 《生成式人工智能服务管理暂行办法》 §12 | 显式标识与日志 | `public_disclosure.ai_disclosure`, `public_disclosure.label_locales[].locale = zh-CN` | reviewer | partial |
| 《互联网信息服务深度合成管理规定》 §16 | 显著标识 | `public_disclosure.label_text_required` | `validate_repo.py` | yes |
| 同 §17 | 投诉举报机制 | `.github/ISSUE_TEMPLATE/takedown-request.yml` | n/a | n/a |
| 同 §18 | 不得用于身份冒充 | `public_profile.allowed_public_interactions` does NOT include `identity_verification`-like values | schema enum | yes |

## Reviewer flow

When you sign off on a `human-record` PR, walk this checklist top-to-bottom:

1. Is the **rights basis** valid for this jurisdiction? If `rights.cross_border_transfer_basis = none` and any artifact's `region` differs from `subject.residency_region`, BLOCK the PR.
2. Is the **separate biometric consent** present whenever any artifact has `sensitivity ∈ {S3_BIOMETRIC, S4_RESTRICTED, S4_IDENTITY}`?
3. Is the record **a minor**? If yes, `visibility` MUST be `private` or `team`. The registry generator already filters this; the reviewer's job is to confirm it.
4. Is the record **deceased** or under legal hold? Confirm `inheritance_policy.default_action_on_death` matches the executor's documented intent. `[需律师审阅]` if there is family conflict.
5. Is `public_disclosure` populated for any `public_*` visibility? Schema rejects without it; reviewer confirms `label_text_required` is in the audience's language.
6. Has `audit/events.jsonl` been initialised with at least a `record_created` event emitted via `tools/emit_audit_event.py`?
7. Sign in `review.reviewer_notes_ref` with a brief markdown record. Set `review.status = approved_public` only after all of the above pass.

## CI enforcement summary

- `tools/lint_schemas.py` — schema well-formedness (Draft 2020-12).
- `tools/validate_repo.py` — every manifest validates against `manifest.schema.json` (incl. the new `if/then` for `public_disclosure`).
- `tools/validate_examples.py` — every `examples/*` archive validates.
- `tools/validate_media.py` — pointer media metadata meets the per-modality minimum from `docs/COLLECTION_STANDARD.md`.
- `tools/test_registry.py` — registry generation honours the minor / private / non-approved exclusions.
- `tools/batch_validate.py` — runs everything and emits a single JSON report for downstream consumers.

## Open items / `[需律师审阅]`

- Cross-border between EU and CN under the EU-China Standard Contract is still
  ambiguous in practice; counsel input required before any record sets
  `cross_border_transfer_status = approved` for that pair.
- C2PA enforcement (EU AI Act §50(2)) requires v1.0+ runtime tooling; v0.4 only
  *declares* the obligation in `public_disclosure`.
- `inheritance_policy` interpretation in jurisdictions outside CN/EU/US is not
  covered by this checklist.
