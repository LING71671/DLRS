# DLRS Hub: Global Digital Life Repository - Complete User Guide

<div align="center">

**Digital Life Repository Standard Hub**

A standardized repository for establishing the "Global Digital Life Initiative"

> **📢 This project is currently in RFC stage. Feedback, translations, schema improvements, and ethical review are welcome.**  
> **本项目目前处于 RFC（征求意见）阶段，欢迎反馈、翻译、Schema 改进和伦理审查。**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/CHANGELOG.md)
[![i18n](https://img.shields.io/badge/i18n-2%20languages-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/tree/master/docs/i18n)

**Languages / 语言:** English | [简体中文](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.md) | [日本語](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.ja.md) 🚧 | [한국어](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.ko.md) 📝

</div>

---

## 📖 Table of Contents

- [What is DLRS Hub?](#what-is-dlrs-hub)
- [Core Concepts](#core-concepts)
- [Quick Start](#quick-start)
- [Detailed Tutorial](#detailed-tutorial)
  - [1. Environment Setup](#1-environment-setup)
  - [2. Create Your First Digital Life Record](#2-create-your-first-digital-life-record)
  - [3. Fill in Record Information](#3-fill-in-record-information)
  - [4. Validation and Submission](#4-validation-and-submission)
- [Directory Structure](#directory-structure)
- [FAQ](#faq)
- [Advanced Usage](#advanced-usage)
- [Contributing](#contributing)
- [Legal Notice](#legal-notice)

---

## What is DLRS Hub?

DLRS Hub (Digital Life Repository Standard Hub) is a **standardized digital life record management system** designed to establish a:

- ✅ **Auditable**: Complete audit logs for all operations
- ✅ **Revocable**: Participants can withdraw authorization and delete data at any time
- ✅ **Verifiable**: Data integrity verified through hashes and signatures
- ✅ **Scalable**: Supports multiple data types and use cases
- ✅ **Privacy-First**: Sensitive data is not stored directly in Git repositories

### What Problem Does This Solve?

DLRS Hub's goal is **not** to dump everyone's raw audio and video directly into GitHub, but to establish a secure, compliant, and controllable digital life record system.

### Five Core Principles

1. **Raw Sensitive Materials Not Directly in Git**  
   Audio, video, documents, faces, voiceprints, and other highly sensitive materials are stored in regionalized object storage. This repository only stores `.pointer.json` pointer files, hash values, and review status.

2. **Voluntary Participation First**  
   Public indexes only accept records that are authorized by the individual, voluntarily participated in, and revocable.

3. **Public Does Not Mean Unlimited Use**  
   Each record must explicitly declare whether it allows: public display, model fine-tuning, voice cloning, avatar cloning, commercialization, and cross-border processing.

4. **Freeze First, Review, Then Delete**  
   When encountering complaints, impersonation, consent withdrawal, or inheritance disputes, freeze the runtime state first and retain necessary audit evidence.

5. **AI-Generated Content Must Be Labeled**  
   All public outputs must be explicitly marked as AI-generated/edited content. Audio and video should additionally include watermarks or C2PA content credentials.

---

## Core Concepts

### Three Core Object Types

| Object | Directory | Purpose |
|--------|-----------|---------|
| **Standards** | `standards/dlrs/` | Define DLRS minimum compliance specifications, directory conventions, permission models, and audit models |
| **Templates** | `templates/` | For new participants to copy and fill in to generate their own digital life records |
| **Human Records** | `humans/{region}/{country}/{record_id_slug}/` | Voluntary participants' record manifests, authorization status, public profiles, and pointers |

### Visibility Levels

- `private`: Completely private, does not appear in any public index
- `public_unlisted`: Accessible via direct link but does not appear in public index
- `public_indexed`: Appears in public index, searchable and discoverable

### Sensitivity Classification

- `S0_PUBLIC`: Public information (e.g., public profile)
- `S1_INTERNAL`: Internal information (e.g., preference settings)
- `S2_CONFIDENTIAL`: Confidential information (e.g., chat logs)
- `S3_BIOMETRIC`: Biometric information (e.g., face, voiceprint)
- `S4_IDENTITY`: Identity documents (e.g., passport, ID card)

---

## Quick Start

### Prerequisites

- Git
- Python 3.8+
- Text editor (VS Code recommended)

### Three Steps to Get Started

```bash
# 1. Clone the repository
git clone https://github.com/your-org/dlrs-hub.git
cd dlrs-hub

# 2. Install dependencies
pip install -r tools/requirements.txt

# 3. View example record
cd humans/asia/cn/dlrs_94f1c9b8_lin-example
cat manifest.json
```

---

## Detailed Tutorial

### 1. Environment Setup

#### 1.1 Install Python Dependencies

```bash
cd dlrs-hub
pip install -r tools/requirements.txt
```

#### 1.2 Verify Tools Are Available

```bash
python tools/validate_repo.py --help
python tools/new_human_record.py --help
```

---

### 2. Create Your First Digital Life Record

#### 2.1 Use Automated Tool to Create Record

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "John Doe" \
  --region americas \
  --country us
```

This will create a new record directory at `humans/americas/us/dlrs_12345678_john-doe/`.

#### 2.2 Manual Creation (Optional)

If you prefer manual creation, copy the template:

```bash
# Copy template to new location
cp -r templates/archive-types/self-owned/ humans/americas/us/dlrs_12345678_john-doe/

# Navigate to new record directory
cd humans/americas/us/dlrs_12345678_john-doe/
```

---

### 3. Fill in Record Information

#### 3.1 Edit `manifest.json` (Core Configuration File)

This is the most important file containing all record metadata.

```json
{
  "schema_version": "0.2.0",
  "record_id": "dlrs_12345678",
  "display_slug": "john-doe",
  "visibility": "private",  // Options: private, public_unlisted, public_indexed
  
  "subject": {
    "type": "self",  // self (individual) or third_party (third-party upload)
    "display_name": "John Doe",
    "legal_name": null,  // Optional: real legal name
    "locale": "en-US",
    "residency_region": "US",
    "is_minor": false,  // Whether the subject is a minor
    "status": "living"  // living or deceased
  },
  
  "rights": {
    "uploader_role": "self",
    "rights_basis": ["consent"],  // Rights basis: consent, contract, legitimate_interest
    "evidence_refs": [
      "consent/consent_statement.md",
      "consent/consent_video.pointer.json"
    ],
    "allow_public_listing": false,  // Allow public indexing
    "allow_commercial_use": false,  // Allow commercial use
    "allow_model_finetune": false,  // Allow model fine-tuning
    "allow_voice_clone": false,     // Allow voice cloning
    "allow_avatar_clone": false,    // Allow avatar cloning
    "allow_research_use": false,    // Allow research use
    "cross_border_transfer_basis": "none",
    "cross_border_transfer_status": "not_needed"
  },
  
  "consent": {
    "captured_at": "2026-04-25T10:30:00-05:00",
    "withdrawal_endpoint": "mailto:your-email@example.com",  // Withdrawal contact
    "separate_biometric_consent": true,
    "guardian_consent": false,
    "consent_version": "0.2.0",
    "allowed_scopes": [
      "storage",
      "structured_processing"
    ]
  },
  
  "artifacts": [],  // Fill in later
  
  "deletion_policy": {
    "allow_delete": true,
    "allow_export": true,
    "withdrawal_effect": "freeze_runtime_then_delete",
    "legal_hold": false
  },
  
  "security": {
    "primary_region": "US",
    "replication_regions": [],
    "encryption_at_rest": true,
    "kms_ref": null,
    "watermark_policy": "visible_and_invisible",
    "c2pa_enabled": false
  },
  
  "review": {
    "status": "pending",  // pending, approved_public, rejected
    "verified_consent_badge": false,
    "public_data_only_badge": false,
    "risk_level": "low",
    "reviewer_notes_ref": null
  },
  
  "audit": {
    "created_at": "2026-04-25T10:45:00-05:00",
    "last_modified_at": "2026-04-25T10:45:00-05:00",
    "change_log_hash": null
  }
}
```

#### 3.2 Edit `public_profile.json` (Public Profile)

If you plan to make your record public, fill in this file:

```json
{
  "display_name": "John Doe",
  "bio": "A technology enthusiast and developer",
  "avatar_url": null,
  "social_links": {
    "github": "https://github.com/johndoe",
    "twitter": null,
    "website": "https://johndoe.example.com"
  },
  "tags": ["developer", "ai", "open-source"],
  "locale": "en-US"
}
```

#### 3.3 Fill in Consent Statement `consent/consent_statement.md`

```markdown
# Digital Life Record Consent Statement

I, John Doe, confirm that:

1. I voluntarily participate in the DLRS Digital Life Initiative
2. I understand how my data will be used
3. I retain the right to withdraw authorization at any time

Signature Date: April 25, 2026
Signatory: John Doe
```

#### 3.4 Add Data Pointers (Do Not Upload Raw Files!)

Create pointer files in the `artifacts/raw_pointers/` directory, e.g., `audio/voice_master.pointer.json`:

```json
{
  "artifact_id": "voice_001",
  "type": "voice_sample",
  "format": "wav",
  "storage_uri": "s3://my-bucket/audio/voice_master.wav",
  "checksum": "sha256:abc123...",
  "size_bytes": 1048576,
  "region": "US",
  "sensitivity": "S3_BIOMETRIC",
  "contains_sensitive_data": true,
  "created_at": "2026-04-25T10:00:00-05:00"
}
```

Also add a reference in the `artifacts` array in `manifest.json`:

```json
"artifacts": [
  {
    "artifact_id": "voice_001",
    "type": "voice_sample",
    "format": "wav",
    "storage_uri": "s3://my-bucket/audio/voice_master.wav",
    "checksum": "sha256:abc123...",
    "region": "US",
    "sensitivity": "S3_BIOMETRIC",
    "contains_sensitive_data": true
  }
]
```

---

### 4. Validation and Submission

#### 4.1 Local Validation

```bash
# Return to repository root
cd /path/to/dlrs-hub

# Run validation tool
python tools/validate_repo.py

# If passed, you'll see:
# ✓ All validations passed
```

#### 4.2 Generate Index (For Public Records)

```bash
python tools/build_registry.py
```

This updates the `registry/humans.index.jsonl` file.

#### 4.3 Commit to Git

```bash
git add humans/americas/us/dlrs_12345678_john-doe/
git commit -m "Add: John Doe's digital life record"
git push
```

#### 4.4 Create Pull Request

If contributing to a public repository, create a PR:

1. Click "New Pull Request" on GitHub
2. Select template: `.github/PULL_REQUEST_TEMPLATE/human-record.md`
3. Fill in PR description
4. Wait for review

---

## Directory Structure

```text
dlrs-hub/
│
├── standards/              # 📜 DLRS Standard Documents
│   └── dlrs/
│       ├── v0.2/          # Versioned standards
│       └── README.md
│
├── schemas/               # 🔍 JSON Schema Validation Rules
│   ├── manifest.schema.json
│   ├── public_profile.schema.json
│   └── pointer.schema.json
│
├── registry/              # 📇 Public Index
│   ├── humans.index.jsonl      # Index of all public records
│   ├── badges.index.json       # Badge system
│   └── regions/               # Regional indexes
│
├── humans/                # 👤 Human Records Directory
│   ├── asia/
│   ├── europe/
│   ├── americas/
│   │   └── us/
│   │       └── dlrs_12345678_john-doe/
│   │           ├── manifest.json           # Core configuration
│   │           ├── public_profile.json     # Public profile
│   │           ├── README.md              # Record description
│   │           ├── consent/               # Consent evidence
│   │           ├── profile/               # Personal profile
│   │           ├── artifacts/             # Data pointers
│   │           ├── derived/              # Derived data
│   │           ├── runtime/              # Runtime configuration
│   │           └── audit/                # Audit logs
│   └── _TEMPLATE/         # Record template
│
├── templates/             # 📋 Various Templates
│   ├── archive-types/
│   │   ├── self-owned/    # Self-upload template
│   │   ├── memorial/      # Memorial record template
│   │   └── research/      # Research use template
│   ├── consent/           # Consent form templates
│   └── pr-packages/       # PR submission package templates
│
├── examples/              # 💡 Example Records (Fictional Data)
│   ├── minimal-private/
│   ├── public-indexed-demo/
│   └── memorial-estate-demo/
│
├── tools/                 # 🛠️ Automation Tools
│   ├── validate_repo.py          # Validation tool
│   ├── build_registry.py         # Index generation tool
│   ├── new_human_record.py       # New record creation tool
│   ├── check_sensitive_files.py  # Sensitive file checker
│   └── requirements.txt
│
├── policies/              # 📋 Policy Documents
│   ├── privacy_policy.md
│   ├── takedown_policy.md
│   ├── minor_protection.md
│   ├── deceased_policy.md
│   └── cross_border.md
│
├── operations/            # 🔧 Operations Manual
│   ├── review_manual.md
│   ├── incident_response.md
│   ├── badge_issuance.md
│   └── sla.md
│
├── api/                   # 🌐 API Specifications
│   ├── openapi.yaml
│   └── websocket-events.md
│
├── docs/                  # 📚 Documentation
│   ├── getting-started.md
│   ├── architecture.md
│   ├── FAQ.md
│   ├── upload-guide.md
│   └── references.md
│
└── .github/               # ⚙️ GitHub Configuration
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE/
    └── workflows/
```

---

## FAQ

### Q1: Why not put videos directly in GitHub?

**A:** Because raw audio, video, faces, voiceprints, and documents are highly sensitive data. GitHub is not suitable for storing large binary files, and once committed, they are difficult to completely delete. The repository should store pointers and audit information, not host originals directly.

### Q2: Must human records be public?

**A:** No. The default is private (`visibility: private`). Public indexing requires additional authorization and review.

### Q3: Does a digital life equal the actual person?

**A:** No. All outputs are only AI-generated or AI-assisted content and do not represent the real person's immediate authentic expression. They must be clearly labeled as AI-generated content.

### Q4: How do I withdraw my record?

**A:** Contact the email or endpoint specified in `consent.withdrawal_endpoint` in `manifest.json`. The system will first freeze the runtime state, then delete the data.

### Q5: Can minors create records?

**A:** Yes, but guardian consent is required (`consent.guardian_consent: true`), and they cannot be publicly indexed.

### Q6: How are records of deceased individuals handled?

**A:** Must have `profile/inheritance_policy.json` specifying heirs and handling methods. The default behavior is to freeze the record.

### Q7: Can I commercially use someone else's record?

**A:** You must check the `rights.allow_commercial_use` field of that record. Unauthorized commercial use is illegal.

### Q8: How do I verify the authenticity of a record?

**A:** Check the `review.verified_consent_badge` badge and the provenance proof in `audit/provenance.json`.

---

## Advanced Usage

### Public Index Admission Criteria

For a record to enter `registry/humans.index.jsonl`, it must meet:

- ✅ `review.status = approved_public`
- ✅ `visibility = public_indexed` or `public_unlisted`
- ✅ `review.verified_consent_badge = true` or `review.public_data_only_badge = true`
- ✅ `rights.allow_public_listing = true`
- ✅ `consent.withdrawal_endpoint` is not empty
- ✅ Minor records cannot be publicly indexed
- ✅ Deceased records must have `profile/inheritance_policy.json`

### Badge System

DLRS Hub provides the following badges:

- 🔵 **verified-consent**: Verified consent
- 🟢 **public-data-only**: Public data only
- 🟡 **research-approved**: Research use approved
- 🔴 **commercial-licensed**: Commercial license

### Review Process

1. Submit PR
2. Automated validation (CI)
3. Manual review
4. Badge issuance
5. Merge to main branch
6. Update public index

### Object Storage Configuration

Recommended services:

- Mainland China: [Alibaba Cloud OSS](https://www.alibabacloud.com/product/object-storage-service), [Tencent Cloud COS](https://www.tencentcloud.com/products/cos)
- International: [AWS S3](https://aws.amazon.com/s3/), [Google Cloud Storage](https://cloud.google.com/storage)
- Self-hosted: [MinIO](https://min.io/)

Configuration example:

```json
{
  "storage_uri": "s3://my-bucket/path/to/file.wav",
  "region": "us-east-1",
  "encryption": "AES256",
  "access_control": "private"
}
```

---

## Contributing

We welcome the following types of contributions:

### 1. Standard Improvements

Use Issue template: `spec_proposal`

### 2. New Human Records

Use PR template: `human-record`

### 3. Tool and Schema Fixes

Regular Pull Request

### 4. Complaints and Takedown Requests

Use Issue template: `takedown`, or send to security email

### Local Development

```bash
# Clone repository
git clone https://github.com/your-org/dlrs-hub.git
cd dlrs-hub

# Install dependencies
pip install -r tools/requirements.txt

# Run tests
python tools/validate_repo.py
python tools/check_sensitive_files.py

# Generate index
python tools/build_registry.py
```

---

## Legal Notice

⚠️ **Important Notice**

This project involves:

- Portrait rights and voice rights
- Biometric information
- Personal information protection
- Rights of the deceased
- Cross-border data transfer
- AI-generated content labeling
- Deepfake abuse risks

**Before official launch, the following must be reviewed by lawyers in the target jurisdiction:**

- All policies in the `policies/` directory
- Consent form templates in `templates/consent/`
- `LEGAL_DISCLAIMER.md`

**Disclaimer:**

The templates and tools provided in this repository are for reference only and do not constitute legal advice. Users are responsible for their own compliance.

---

## Version Information

- Current Version: **v0.2.0**
- Release Date: April 25, 2026
- Status: Draft

View complete changelog: [CHANGELOG.md](CHANGELOG.md)

---

## Related Resources

- 📖 [Complete Documentation](docs/)
- 🗺️ [Project Roadmap](ROADMAP.md) - Long-term planning and version schedule
- 🎯 [Implementation Status](docs/IMPLEMENTATION_STATUS.md) - Current progress summary
- 📊 [Gap Analysis](docs/GAP_ANALYSIS.md) - Detailed comparison with ultimate standard
- 🚀 [Ultimate Standard](DLRS_ULTIMATE.md) - Complete industry standard draft
- 🏗️ [Architecture Design](docs/architecture.md)
- ❓ [FAQ](docs/FAQ.md)
- 🤝 [Contributing Guide](CONTRIBUTING.md)
- 🌍 [Internationalization (i18n)](docs/i18n/) - Translation guides and multilingual support
- 📜 [Code of Conduct](CODE_OF_CONDUCT.md)
- 🏛️ [Governance Model](GOVERNANCE.md)

---

## Contact

- Issue Reporting: [GitHub Issues](https://github.com/your-org/dlrs-hub/issues)
- Security Issues: security@example.org
- General Inquiries: contact@example.org

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

<div align="center">

**Making Digital Life Safer, More Transparent, and More Controllable**

Made with ❤️ by DLRS Community

</div>
