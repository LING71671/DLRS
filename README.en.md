# Digital Life Repository Standard (DLRS) v0.6.0

<div align="center">

**DLRS defines the `.life` runnable digital-life archive standard** — a **dual standard**:

1. **`.life` archive file format** — a portable, signed, time-bounded digital-life archive package, generated under the consent of the subject (or an authorised representative).
2. **`.life` runtime protocol** — how compatible runtimes load `.life` to produce an *AI digital life instance* in chat / virtual world / 3D / other digital environments.

Privacy-first, consent-based, structured, revocable, auditable, schema-validated, template-submitted.  
**`.life` is NOT a "resurrection" technology** — a runtime mounting a `.life` produces an always-identifiable *AI digital life instance*, which MUST remain revocable and auditable.

> **📢 RFC Stage**  
> This is an early-stage open standard draft. Feedback, translations, schema improvements, and ethical review are welcome.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/LICENSE)
[![Version](https://img.shields.io/badge/version-v0.6.0-orange.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/releases/tag/v0.6.0)
[![i18n](https://img.shields.io/badge/i18n-2%20languages-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/tree/master/docs/i18n)
[![RFC](https://img.shields.io/badge/RFC-Open%20for%20Comment-green.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/docs/community/RFC-DLRS-v0.2.md)

**Languages:** English | [简体中文](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.md)

</div>

---

## 🎯 What is DLRS?

**DLRS (Digital Life Repository Standard)** is an **open standard draft** comprising two paired standards:

### 📦 The `.life` archive file format

A `.life` file is a **portable, signed, time-bounded digital-life archive package**, generated under the consent of the subject (or an authorised representative). It can include:

- Identity description, consent evidence, verification level
- Memory structures (memory atoms, knowledge graph)
- Personality preferences, `forbidden_uses[]` list
- Multimodal asset pointers (pointer mode) or encrypted blobs (encrypted mode)
- Model references, `withdrawal_endpoint`
- A hash-chained subset of the source record's audit log

Spec: [`docs/LIFE_FILE_STANDARD.md`](docs/LIFE_FILE_STANDARD.md) ·
Schema: [`schemas/life-package.schema.json`](schemas/life-package.schema.json).

### 🚀 The `.life` runtime protocol

Compatible runtimes load a `.life` and, per the protocol, produce **an interactive, revocable, auditable AI digital life instance** in chat applications, virtual worlds, 3D scenes, or other digital environments. A runtime MUST:

- Tag every output as *AI digital life instance* (never claim equivalence to the human)
- Enforce `forbidden_uses[]`
- Re-poll `withdrawal_endpoint` at session start AND at least every 24h
- Refuse to mount after `expires_at`
- Never combine memories from two `.life` files into one instance

Spec: [`docs/LIFE_RUNTIME_STANDARD.md`](docs/LIFE_RUNTIME_STANDARD.md).

### 🧩 Supporting infrastructure

DLRS also defines the underlying structures that the `.life` standard rests on:

- 📋 DLRS repository / archive directory structure and JSON schemas (stable as of v0.6)
- ✅ Consent and withdrawal models
- 🔒 Privacy boundaries and sensitivity levels
- 🏛️ Governance rules and review processes
- 🛠️ Validation tools and archive templates
- ⚖️ Legal disclaimers and ethical guidelines

---

## ❌ What DLRS is NOT

**Important Clarifications**:

- ❌ **NOT** a technology to "resurrect" or "clone" humans — a `.life` mounted by a runtime produces an *AI digital life instance*, which is never equivalent to the underlying human
- ❌ **NOT** a consent-free / withdrawal-free post-mortem reanimation tool — every `.life` MUST declare a working `withdrawal_endpoint`, and every runtime MUST honour withdrawal in real time
- ❌ **NOT** a guarantee that AI avatars equal real persons
- ❌ **NOT** a guarantee of legal compliance
- ❌ **NOT** a permanent storage solution — every `.life` MUST declare `expires_at`; runtimes MUST refuse to mount after it
- ❌ **NOT** a mature production system — this repo currently ships specs + schema + an example builder; **no reference runtime implementation is shipped** (deferred to v0.8+)
- ❌ **NOT** a substitute for legal advice

---

## ✅ What DLRS IS

- ✅ **`.life` dual standard**: file format + runtime protocol, each on its own semver track
- ✅ **Open standard draft**: For discussion and improvement
- ✅ **Privacy-first**: Sensitive data not stored directly in Git; pointer-mode `.life` files do not embed raw assets by default
- ✅ **Consent-based**: All archives must have clear consent evidence; every `.life` MUST declare `issued_by` + `consent_evidence_ref` + `verification_level`
- ✅ **Revocable**: Users can withdraw consent at any time; `.life` mandates `withdrawal_endpoint`, runtimes MUST poll it
- ✅ **Auditable**: All actions are logged on a hash chain; `.life` embeds an audit subset
- ✅ **Always identifiable**: a runtime mounting a `.life` MUST always identify the result as an *AI digital life instance* (`ai_disclosure` minimum is `visible_label_required`)
- ✅ **Time-bounded**: every `.life` MUST declare `expires_at`; runtimes MUST refuse to mount after it
- ✅ **Experimental**: Non-binding reference implementation
- ✅ **Community-driven**: Contributions and feedback welcome

---

## 🚀 Why DLRS?

As AI technology advances, digital life archives are becoming increasingly important. However, there's currently a lack of:

1. **Standardized archive structure** - Every project reinvents the wheel
2. **Clear consent model** - How to prove user consent? How to revoke?
3. **Privacy protection framework** - What data should never be stored? How to reference safely?
4. **Governance and review rules** - How to handle disputes? How to verify authenticity?
5. **Ethical boundary definitions** - What should be forbidden even with consent?

DLRS attempts to address these issues through an open standard approach.

---

## 📖 Core Concepts

### Three-Layer Architecture

```
Git Repository (Public/Private)
├── manifest.json          # Metadata and configuration
├── consent/               # Consent evidence (may use pointers)
├── artifacts/raw_pointers/ # Pointer files (no raw data)
└── audit/                 # Audit logs

External Storage (Encrypted, Access-Controlled)
├── s3://bucket/voice/master.wav
├── s3://bucket/video/training.mp4
└── s3://bucket/images/headshot.jpg
```

### Sensitivity Levels

- `S0_PUBLIC` - Public information (e.g., public bio)
- `S1_INTERNAL` - Internal information (e.g., preferences)
- `S2_CONFIDENTIAL` - Confidential information (e.g., chat logs)
- `S3_BIOMETRIC` - Biometric information (e.g., face, voice)
- `S4_IDENTITY` - Identity documents (e.g., passport, ID)

### Visibility Levels

- `private` - Completely private
- `public_unlisted` - Accessible via direct link
- `public_indexed` - Searchable and discoverable

---

## 🏁 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Digital-Life-Repository-Standard/DLRS.git
cd DLRS
```

### 2. Install Dependencies

```bash
pip install -r tools/requirements.txt
```

### 3. View Example Archive

```bash
cd examples/minimal-private
cat manifest.json
```

### 4. Create Your First Archive

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "John Doe" \
  --region americas \
  --country us
```

### 5. Validate Archive

```bash
python tools/validate_repo.py
```

---

## 📚 Documentation

- 📖 [Getting Started Guide](docs/getting-started.en.md)
- 🤔 [FAQ](docs/FAQ.en.md)
- 🏗️ [Architecture](docs/architecture.md)
- 📋 [RFC: DLRS v0.2](docs/community/RFC-DLRS-v0.2.md)
- 💬 [Consent Model Feedback](docs/community/consent-model-feedback.md)
- 🎯 [Good First Issues](docs/community/good-first-issues.md)
- 📢 [Community Promotion Guide](docs/community/community-promotion-guide.md)

---

## 🤝 How to Contribute

We welcome the following types of contributions:

1. **Feedback and Suggestions** - Submit issues or participate in discussions
2. **Documentation Improvements** - Fix errors, add examples, translate docs
3. **Schema Improvements** - Optimize JSON schema design
4. **Tool Development** - Improve validation tools, add new features
5. **Example Archives** - Provide more templates and examples
6. **Ethical Review** - Point out potential ethical and legal risks

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 🌍 Internationalization

Currently supported languages:
- 🇺🇸 English
- 🇨🇳 简体中文

Welcome contributions for more language translations! See [i18n guide](docs/i18n/)

---

## 📊 Current Status

**Version**: v0.6.0  
**Status**: RFC (Request for Comments) stage  
**Completion**: Approximately 88% (v0.6.0 release)

### ✅ Completed
- Basic directory structure
- JSON schema definitions
- Consent and withdrawal model
- Privacy boundary definitions
- Validation tools
- Example archives
- Bilingual documentation

### 🚧 In Progress
- Community feedback collection
- Schema optimization
- Documentation refinement
- Multi-language translation

### 📋 Planned
- Media collection standards
- Build pipelines
- Runtime systems
- Permission and audit implementation

See [ROADMAP.md](ROADMAP.md) and [Implementation Status](docs/IMPLEMENTATION_STATUS.md)

---

## ⚖️ Legal and Ethical Considerations

**Important Reminders**:

This project involves:
- Portrait rights and voice rights
- Biometric information
- Personal information protection
- Rights of deceased persons
- Cross-border data transfers
- AI-generated content labeling
- Deepfake abuse risks

**Disclaimer**:
- Templates and tools provided in this repository are for reference only and do not constitute legal advice
- Users are responsible for their own compliance
- Must consult legal professionals before formal use

See [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md)

---

## 📞 Contact

- 💬 [GitHub Discussions](https://github.com/Digital-Life-Repository-Standard/DLRS/discussions)
- 🐛 [Issues](https://github.com/Digital-Life-Repository-Standard/DLRS/issues)
- 📧 Security issues: See [SECURITY.md](SECURITY.md)

---

## 📄 License

This project is licensed under [MIT License](LICENSE).

---

## 🙏 Acknowledgments

Thanks to all contributors and community members for their support!

---

## 🔗 Related Resources

- [Complete Standard Draft](DLRS_ULTIMATE.md)
- [Gap Analysis](docs/GAP_ANALYSIS.md)
- [Implementation Status](docs/IMPLEMENTATION_STATUS.md)
- [Project Roadmap](ROADMAP.md)
- [Governance Model](GOVERNANCE.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

---

<div align="center">

**Making digital life archives safer, more transparent, and more controllable**

Made with ❤️ by DLRS Community

</div>
