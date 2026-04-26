<!--
Translation Status: ✅ Complete
Based on: docs/FAQ.md (v0.2.0)
Target Locale: en-US (English)
Last Updated: 2026-04-25
Translator: DLRS Core Team
-->

# Frequently Asked Questions (FAQ)

**Languages / 语言:** English | [简体中文](FAQ.md)

---

## General Questions

### What is DLRS Hub?

DLRS Hub (Digital Life Repository Standard Hub) is a standardized system for managing digital life records. It provides a framework for storing, organizing, and controlling access to digital representations of individuals, including voice samples, images, videos, and personal data.

### Who is DLRS Hub for?

DLRS Hub is designed for:
- **Individuals** who want to preserve their digital legacy
- **Families** managing memorial records of deceased loved ones
- **Researchers** studying digital identity and AI ethics
- **Organizations** building digital human applications
- **Developers** creating AI voice/avatar cloning systems

### Is DLRS Hub free to use?

Yes, DLRS Hub is open source under the MIT License. You can use, modify, and distribute it freely.

---

## Technical Questions

### Why not put videos directly in GitHub?

**Answer**: Raw audio, video, facial data, voiceprints, and identity documents are highly sensitive data. GitHub is not suitable for storing large binary files because:

1. **Size limitations**: Git repositories become slow and bloated with large files
2. **Permanent history**: Once committed, files are difficult to completely remove from Git history
3. **Privacy risks**: Sensitive biometric data should not be in public version control
4. **Compliance**: Many jurisdictions require specific security measures for biometric data

Instead, DLRS Hub stores **pointer files** (`.pointer.json`) that reference data in secure object storage (S3, OSS, etc.), while keeping metadata and audit information in Git.

### What is a pointer file?

A pointer file is a JSON file that contains metadata about a file stored elsewhere:

```json
{
  "artifact_id": "voice_001",
  "type": "voice_sample",
  "storage_uri": "s3://my-bucket/audio/voice.wav",
  "checksum": "sha256:abc123...",
  "size_bytes": 1048576,
  "sensitivity": "S3_BIOMETRIC"
}
```

This approach separates sensitive data from version control while maintaining traceability.

### What object storage services are supported?

DLRS Hub supports any S3-compatible object storage:
- **AWS S3** (International)
- **Alibaba Cloud OSS** (China)
- **Tencent Cloud COS** (China)
- **Google Cloud Storage** (International)
- **MinIO** (Self-hosted)
- **Backblaze B2** (International)

### How do I validate my record?

Run the validation tool:

```bash
python tools/validate_repo.py
```

This checks:
- JSON schema compliance
- Required fields presence
- File structure correctness
- Sensitive file detection
- Consent documentation

---

## Privacy and Consent

### Must human records be public?

**No.** Records are **private by default** (`visibility: private`). Public indexing requires:
- Explicit authorization (`allow_public_listing: true`)
- Verified consent badge
- Manual review approval

You can also use `public_unlisted` for records accessible via direct link but not searchable.

### How do I withdraw my consent?

Contact the endpoint specified in your `manifest.json`:

```json
"consent": {
  "withdrawal_endpoint": "mailto:privacy@example.org"
}
```

The system will:
1. **Freeze** the runtime state immediately
2. **Preserve** audit logs (required by law)
3. **Delete** personal data after retention period
4. **Remove** from public indexes

### Can minors create records?

Yes, but with restrictions:
- Guardian consent required (`consent.guardian_consent: true`)
- Cannot be publicly indexed
- Additional privacy protections apply
- Must comply with COPPA (US), GDPR (EU), or local laws

### What about deceased individuals?

Records of deceased individuals require:
- `status: "deceased"` in manifest
- `profile/inheritance_policy.json` specifying heirs
- Executor contact information
- Default action: freeze the record

---

## Usage and Rights

### Does a digital life equal the actual person?

**No.** This is critically important to understand:

- All outputs are **AI-generated or AI-assisted content**
- They do **not** represent the real person's immediate authentic thoughts
- They are **simulations** based on training data
- All outputs **must be labeled** as AI-generated

Think of it as a digital memorial or assistant, not a replacement for the actual person.

### Can I use someone else's record commercially?

**Only if explicitly authorized.** Check the record's `manifest.json`:

```json
"rights": {
  "allow_commercial_use": true,  // Must be true
  "allow_voice_clone": true,     // For voice applications
  "allow_avatar_clone": true     // For avatar applications
}
```

Unauthorized commercial use is:
- Violation of the record's license
- Potentially illegal (right of publicity, personality rights)
- Subject to takedown and legal action

### What can I do with a public record?

It depends on the permissions granted:

| Permission | Allowed Use |
|------------|-------------|
| `allow_public_listing` | View in public index |
| `allow_model_finetune` | Train AI models |
| `allow_voice_clone` | Create voice synthesis |
| `allow_avatar_clone` | Create digital avatars |
| `allow_commercial_use` | Commercial applications |
| `allow_research_use` | Academic research |

Always check the specific record's permissions before use.

### How do I verify a record's authenticity?

Check for these indicators:

1. **Verified Consent Badge** (`review.verified_consent_badge: true`)
2. **Provenance Information** in `audit/provenance.json`
3. **Consent Evidence** in `consent/` directory
4. **Review Status** (`review.status: "approved_public"`)
5. **Audit Trail** in `audit/access_log.pointer.json`

Be cautious of records without these verifications.

---

## Compliance and Legal

### Is DLRS Hub GDPR compliant?

DLRS Hub provides **tools and frameworks** for GDPR compliance, but:

⚠️ **You are responsible** for ensuring your specific implementation complies with GDPR and other regulations.

The framework supports:
- Right to access (data export)
- Right to erasure (deletion policy)
- Right to rectification (version control)
- Data portability (JSON format)
- Consent management (consent records)

**Recommendation**: Consult with a lawyer before deploying in production.

### What about CCPA, PIPEDA, or other privacy laws?

The same principle applies: DLRS Hub provides the framework, but you must ensure compliance with applicable laws in your jurisdiction.

Consider:
- **US**: CCPA (California), COPPA (children)
- **Canada**: PIPEDA
- **China**: PIPL (Personal Information Protection Law)
- **Japan**: APPI (Act on Protection of Personal Information)
- **South Korea**: PIPA (Personal Information Protection Act)

### Do I need a lawyer?

**Yes, if you're deploying this in production.** Especially for:
- Public-facing services
- Commercial applications
- Cross-border data transfers
- Services involving minors
- Memorial/deceased records

The templates in `policies/` and `templates/consent/` are **starting points only**, not legal advice.

---

## Badges and Review

### What are badges?

Badges indicate verification status:

- 🔵 **verified-consent**: Consent has been verified by reviewers
- 🟢 **public-data-only**: Contains only public information (no biometrics)
- 🟡 **research-approved**: Approved for academic research
- 🔴 **commercial-licensed**: Licensed for commercial use

### How do I get a verified-consent badge?

1. Submit a record with complete consent documentation
2. Include consent statement (`consent/consent_statement.md`)
3. Provide consent video or signature (`consent/consent_video.pointer.json`)
4. Pass automated validation
5. Pass manual review by maintainers
6. Badge is issued in `review.verified_consent_badge`

### What is the review process?

1. **Automated validation**: Schema, structure, sensitive files
2. **Human review**: Consent verification, content moderation
3. **Badge issuance**: Verified badges added to manifest
4. **Public indexing**: Record added to `registry/humans.index.jsonl`
5. **Ongoing monitoring**: Periodic re-verification

---

## Troubleshooting

### My validation is failing. What should I do?

1. Read the error message carefully
2. Check the example record: `humans/asia/cn/dlrs_94f1c9b8_lin-example/`
3. Verify all required fields are present
4. Ensure JSON syntax is valid
5. Run `python tools/check_sensitive_files.py`
6. Check the [Getting Started Guide](getting-started.md)

### I accidentally committed a large file. How do I remove it?

```bash
# Remove from Git history (use with caution!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/large/file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (only if you're sure!)
git push origin --force --all
```

Better: Use `.pointer.json` files from the start!

### How do I update an existing record?

1. Edit the files in your record directory
2. Update `audit.last_modified_at` in `manifest.json`
3. Run validation: `python tools/validate_repo.py`
4. Commit and push changes
5. If public, the registry will be updated automatically

---

## Contributing and Community

### How can I contribute?

See the [Contributing Guide](../CONTRIBUTING.md) for details. You can:
- Add your own record
- Improve documentation
- Fix bugs in tools
- Translate to other languages
- Propose standard improvements

### Where can I get help?

- **GitHub Issues**: https://github.com/Digital-Life-Repository-Standard/DLRS/issues
- **Email**: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- **Security Issues**: https://github.com/Digital-Life-Repository-Standard/DLRS/security/advisories/new
- **Documentation**: [docs/](.)

### Can I use DLRS Hub for my project?

Yes! DLRS Hub is open source (MIT License). You can:
- Use it as-is
- Fork and modify it
- Build commercial services on top
- Contribute improvements back

Just ensure you comply with applicable privacy laws.

---

## Advanced Topics

### What is the difference between `derived/` and `artifacts/`?

- **`artifacts/`**: Original source materials (audio, video, images)
- **`derived/`**: Processed data derived from artifacts (embeddings, memory atoms, entity graphs)

Derived data is typically generated by AI/ML pipelines and is less sensitive than raw artifacts.

### How do cross-border transfers work?

Check the record's `rights.cross_border_transfer_basis`:

- `none`: No cross-border transfer allowed
- `consent`: Allowed with explicit consent
- `contract`: Allowed under contractual terms
- `adequacy`: Allowed to jurisdictions with adequate protection
- `scc`: Allowed under Standard Contractual Clauses

Always verify compliance with GDPR Article 44-50 or equivalent local laws.

### Can I host my own DLRS Hub instance?

Yes! DLRS Hub is designed to be self-hosted:

1. Clone the repository
2. Set up object storage (S3, MinIO, etc.)
3. Configure access controls
4. Deploy validation tools
5. Set up CI/CD for automated checks

See [Architecture](architecture.md) for deployment guidance.

---

## Still Have Questions?

If your question isn't answered here:

1. Check the [complete documentation](.)
2. Search [GitHub Issues](https://github.com/Digital-Life-Repository-Standard/DLRS/issues)
3. Open a new issue with the `question` label
4. Email us at https://github.com/Digital-Life-Repository-Standard/DLRS/discussions

We're here to help! 💙
