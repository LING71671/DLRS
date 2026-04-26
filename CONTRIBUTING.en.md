<!--
Translation Status: ✅ Complete
Based on: CONTRIBUTING.md (v0.2.0)
Target Locale: en-US (English)
Last Updated: 2026-04-25
Translator: DLRS Core Team
-->

# Contributing to DLRS Hub

**Languages / 语言:** English | [简体中文](CONTRIBUTING.md)

---

Thank you for your interest in contributing to DLRS Hub! We welcome contributions of all kinds, from documentation improvements to new features.

## 🌟 Ways to Contribute

There are many ways to contribute to DLRS Hub:

- 📝 **Add your digital life record** (if you're a voluntary participant)
- 🐛 **Report bugs** or issues
- 💡 **Suggest new features** or improvements
- 📖 **Improve documentation**
- 🌍 **Translate to other languages**
- 🔧 **Fix bugs** or implement features
- 🎨 **Improve schemas** or templates
- 🧪 **Add tests** or validation rules
- 📊 **Propose standard improvements**

## 📋 Contribution Types

| Type | Entry Point | Template/Label |
|------|-------------|----------------|
| **Standard Improvements** | GitHub Issue | `spec_proposal` |
| **New Human Record** | Pull Request | `human-record` template |
| **Bug Fixes** | Pull Request | `bug` label |
| **Schema/Tool Fixes** | Pull Request | `enhancement` label |
| **Documentation** | Pull Request | `documentation` label |
| **Translation** | Pull Request | `[i18n]` prefix |
| **Complaints/Takedown** | GitHub Issue or Email | `takedown` template |

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/DLRS.git
cd DLRS

# Add upstream remote
git remote add upstream https://github.com/Digital-Life-Repository-Standard/DLRS.git
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install -r tools/requirements.txt

# Verify installation
python tools/validate_repo.py --help
```

### 3. Create a Branch

```bash
# Create a new branch for your contribution
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

## 📝 Adding a Human Record

### Minimum Requirements

Before submitting a human record, ensure:

1. ✅ **No raw sensitive files** - Use `.pointer.json` files only
2. ✅ **Complete manifest** - `manifest.json` with all required fields
3. ✅ **Public profile** (if public) - `public_profile.json` for public records
4. ✅ **Consent evidence** - Pointers to consent documentation
5. ✅ **Validation passes** - All automated checks pass
6. ✅ **Manual review** (for public) - Public records require human review

### Step-by-Step Process

#### 1. Create Record Structure

```bash
# Use the automated tool
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "Your Name" \
  --region americas \
  --country us
```

#### 2. Fill in Required Files

**Mandatory files:**
- `manifest.json` - Core configuration
- `consent/consent_statement.md` - Consent statement
- `consent/consent_video.pointer.json` or `consent/signer_signature.json` - Consent proof

**For public records, also include:**
- `public_profile.json` - Public profile information
- `README.md` - Record description

#### 3. Add Data Pointers

⚠️ **Critical**: Do NOT commit large binary files!

Create pointer files in `artifacts/raw_pointers/`:

```json
{
  "artifact_id": "voice_001",
  "type": "voice_sample",
  "storage_uri": "s3://your-bucket/audio/voice.wav",
  "checksum": "sha256:...",
  "sensitivity": "S3_BIOMETRIC"
}
```

#### 4. Validate Locally

```bash
# Run validation
python tools/validate_repo.py

# Check for sensitive files
python tools/check_sensitive_files.py

# Build registry (if public)
python tools/build_registry.py
```

#### 5. Submit Pull Request

```bash
# Commit your changes
git add humans/americas/us/dlrs_12345678_your-name/
git commit -m "Add: Your Name's digital life record"

# Push to your fork
git push origin feature/add-your-record

# Open PR on GitHub using the human-record template
```

### Public Record Admission Criteria

For a record to be publicly indexed, it must meet:

- ✅ `review.status = "approved_public"`
- ✅ `visibility = "public_indexed"` or `"public_unlisted"`
- ✅ `review.verified_consent_badge = true` OR `review.public_data_only_badge = true`
- ✅ `rights.allow_public_listing = true`
- ✅ `consent.withdrawal_endpoint` is not empty
- ✅ Not a minor (`subject.is_minor = false`)
- ✅ If deceased, must have `profile/inheritance_policy.json`

## 🐛 Reporting Bugs

### Before Reporting

1. Check if the issue already exists
2. Try the latest version
3. Gather relevant information (error messages, logs, etc.)

### Bug Report Template

```markdown
**Description**
A clear description of the bug.

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., Windows 11, macOS 13, Ubuntu 22.04]
- Python version: [e.g., 3.10.5]
- DLRS Hub version: [e.g., v0.2.0]

**Additional Context**
Any other relevant information.
```

## 💡 Proposing Features

### Feature Request Template

```markdown
**Problem Statement**
What problem does this feature solve?

**Proposed Solution**
How would you solve it?

**Alternatives Considered**
What other approaches did you consider?

**Additional Context**
Any mockups, examples, or references.
```

## 🔧 Code Contributions

### Code Style

- **Python**: Follow PEP 8
- **JSON**: 2-space indentation
- **Markdown**: Use consistent formatting
- **Comments**: Write clear, concise comments

### Testing

Before submitting:

```bash
# Run validation on entire repository
python tools/validate_repo.py

# Check for sensitive files
python tools/check_sensitive_files.py

# Test your specific changes
python tools/validate_manifest.py path/to/manifest.json
```

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good
git commit -m "Add: Voice cloning permission field to manifest schema"
git commit -m "Fix: Validation error for nested consent objects"
git commit -m "Docs: Update FAQ with cross-border transfer info"

# Bad
git commit -m "update"
git commit -m "fix bug"
git commit -m "changes"
```

### Pull Request Guidelines

1. **Use the appropriate template** (human-record, bug-fix, feature, etc.)
2. **Fill in all sections** of the PR template
3. **Link related issues** using `Fixes #123` or `Relates to #456`
4. **Keep PRs focused** - One feature/fix per PR
5. **Update documentation** if you change functionality
6. **Add tests** if applicable
7. **Ensure CI passes** before requesting review

## 🌍 Translation Contributions

We welcome translations to make DLRS Hub accessible globally!

### Translation Process

1. Check [i18n status](docs/i18n/README.md)
2. Create translation using the helper tool:

```bash
python tools/i18n_helper.py create ja-JP README.md
```

3. Translate the content (see [i18n guidelines](docs/i18n/CONTRIBUTING.md))
4. Submit PR with `[i18n]` prefix:

```bash
git commit -m "[i18n] Add Japanese translation for README"
```

### Translation Priority

1. **High**: README, getting-started, FAQ
2. **Medium**: Policy documents
3. **Low**: Operations manuals

## 📊 Proposing Standard Changes

For changes to the DLRS standard itself:

### 1. Open a Spec Proposal Issue

Use the `spec_proposal` template and include:

- **Motivation**: Why is this change needed?
- **Proposal**: What exactly should change?
- **Impact**: Who/what does this affect?
- **Alternatives**: What other options were considered?
- **Migration**: How do existing records migrate?

### 2. Discussion Period

The community will discuss the proposal. Be prepared to:
- Answer questions
- Refine the proposal
- Consider feedback

### 3. Implementation

Once approved:
- Update schemas in `schemas/`
- Update documentation
- Update templates
- Provide migration guide
- Update version number

## 🚨 Reporting Security Issues

**Do NOT open public issues for security vulnerabilities!**

Instead:
- Email: https://github.com/Digital-Life-Repository-Standard/DLRS/security/advisories/new
- Use GitHub Security Advisories (if available)
- Provide detailed information privately

We will:
1. Acknowledge receipt within 48 hours
2. Investigate and develop a fix
3. Coordinate disclosure timeline
4. Credit you (if desired) in security advisory

## 🚫 Takedown Requests

If you need to report:
- Impersonation
- Unauthorized use of your likeness
- Copyright infringement
- Privacy violations

### Process

1. **Use the takedown issue template** OR
2. **Email**: https://github.com/Digital-Life-Repository-Standard/DLRS/security/advisories/new with:
   - Your identity and contact info
   - Record ID in question
   - Nature of the complaint
   - Evidence supporting your claim

### What Happens Next

1. **Immediate freeze**: Record is frozen (not deleted)
2. **Investigation**: We review the claim
3. **Resolution**: 
   - Valid claim → Record removed
   - Invalid claim → Record restored
   - Dispute → Mediation process

## 📜 Code of Conduct

All contributors must follow our [Code of Conduct](CODE_OF_CONDUCT.md).

In summary:
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

## 🎓 Learning Resources

New to contributing? Check out:

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)
- [Markdown Guide](https://www.markdownguide.org/)
- [JSON Schema Tutorial](https://json-schema.org/learn/)

## 🏆 Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Project README
- Annual contributor highlights

## 📞 Getting Help

Need help with your contribution?

- **General questions**: Open a GitHub Discussion
- **Technical issues**: Open a GitHub Issue
- **Email**: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- **Documentation**: [docs/](docs/)

## 📄 License

By contributing to DLRS Hub, you agree that your contributions will be licensed under the MIT License.

---

## Thank You! 🙏

Every contribution, no matter how small, helps make DLRS Hub better for everyone. We appreciate your time and effort!

**Happy Contributing!** 💙
