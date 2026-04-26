<!--
Translation Status: ✅ Complete
Based on: docs/getting-started.md (v0.2.0)
Target Locale: en-US (English)
Last Updated: 2026-04-25
Translator: DLRS Core Team
-->

# Getting Started

**Languages / 语言:** English | [简体中文](getting-started.md)

---

This guide will help you set up DLRS Hub and create your first digital life record.

## Prerequisites

Before you begin, ensure you have:

- **Git** installed on your system
- **Python 3.8+** installed
- A **text editor** (VS Code, Sublime Text, etc.)
- Basic familiarity with command line

## Step 1: Set Up the Repository

### Clone or Initialize

If you're starting fresh:

```bash
# Initialize a new Git repository
git init DLRS
cd DLRS

# Or clone an existing repository
git clone https://github.com/Digital-Life-Repository-Standard/DLRS.git
cd DLRS
```

### Install Dependencies

```bash
# Install Python dependencies
pip install -r tools/requirements.txt

# Verify installation
python tools/validate_repo.py --help
```

You should see the help message for the validation tool.

## Step 2: Create Your First Human Record

### Option A: Using the Automated Tool (Recommended)

The easiest way to create a new record is using the `new_human_record.py` tool:

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "John Doe" \
  --region americas \
  --country us
```

**Parameters:**
- `--record-id`: Unique identifier (format: `dlrs_` + 8 characters)
- `--display-name`: Display name for the record
- `--region`: Geographic region (asia, europe, americas, africa, oceania)
- `--country`: Country code (ISO 3166-1 alpha-2, e.g., us, cn, jp)

This creates a new directory structure at:
```
humans/americas/us/dlrs_12345678_john-doe/
```

### Option B: Manual Creation

If you prefer manual setup:

```bash
# Copy the template
cp -r humans/_TEMPLATE/ humans/americas/us/dlrs_12345678_john-doe/

# Navigate to the new directory
cd humans/americas/us/dlrs_12345678_john-doe/
```

## Step 3: Fill in Record Information

### Edit manifest.json

This is the core configuration file. Open `manifest.json` and update:

```json
{
  "schema_version": "0.2.0",
  "record_id": "dlrs_12345678",
  "display_slug": "john-doe",
  "visibility": "private",
  
  "subject": {
    "type": "self",
    "display_name": "John Doe",
    "locale": "en-US",
    "residency_region": "US",
    "is_minor": false,
    "status": "living"
  },
  
  "rights": {
    "uploader_role": "self",
    "rights_basis": ["consent"],
    "allow_public_listing": false,
    "allow_commercial_use": false,
    "allow_model_finetune": false,
    "allow_voice_clone": false,
    "allow_avatar_clone": false
  },
  
  "consent": {
    "captured_at": "2026-04-25T10:30:00-05:00",
    "withdrawal_endpoint": "mailto:your-email@example.com"
  }
}
```

### Edit public_profile.json (Optional)

If you plan to make your record public:

```json
{
  "display_name": "John Doe",
  "bio": "A technology enthusiast and developer",
  "locale": "en-US",
  "tags": ["developer", "ai", "open-source"]
}
```

### Add Consent Statement

Edit `consent/consent_statement.md`:

```markdown
# Digital Life Record Consent Statement

I, John Doe, confirm that:

1. I voluntarily participate in the DLRS Digital Life Initiative
2. I understand how my data will be used
3. I retain the right to withdraw authorization at any time

Signature Date: April 25, 2026
Signatory: John Doe
```

### Add Data Pointers (Not Raw Files!)

⚠️ **Important**: Do NOT commit large binary files (audio, video, images) directly to Git.

Instead, create pointer files in `artifacts/raw_pointers/`:

**Example: `artifacts/raw_pointers/audio/voice_master.pointer.json`**

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
  "contains_sensitive_data": true
}
```

## Step 4: Validate Your Record

Before committing, validate your record:

```bash
# Return to repository root
cd /path/to/DLRS

# Run validation
python tools/validate_repo.py
```

If validation passes, you'll see:
```
✓ All validations passed
✓ humans/americas/us/dlrs_12345678_john-doe/manifest.json is valid
```

If there are errors, the tool will show what needs to be fixed.

## Step 5: Build Registry (For Public Records)

If your record is public (`visibility: public_indexed` or `public_unlisted`):

```bash
python tools/build_registry.py
```

This updates the `registry/humans.index.jsonl` file.

## Step 6: Commit and Push

```bash
# Add your new record
git add humans/americas/us/dlrs_12345678_john-doe/

# Commit with descriptive message
git commit -m "Add: John Doe's digital life record"

# Push to remote
git push origin main
```

## Step 7: Submit Pull Request (For Public Repositories)

If you're contributing to a public DLRS Hub:

1. **Fork the repository** on GitHub
2. **Create a new branch**: `git checkout -b add-john-doe-record`
3. **Push your branch**: `git push origin add-john-doe-record`
4. **Open a Pull Request** on GitHub
5. **Select the template**: `.github/PULL_REQUEST_TEMPLATE/human-record.md`
6. **Fill in the PR description**:
   - Record ID
   - Visibility level
   - Consent verification method
   - Any special considerations
7. **Wait for review** from maintainers

## Common Issues and Solutions

### Issue: Validation fails with "Missing required field"

**Solution**: Check that all required fields in `manifest.json` are filled in. Compare with the example in `humans/asia/cn/dlrs_94f1c9b8_lin-example/`.

### Issue: "Record ID already exists"

**Solution**: Choose a different record ID. Each ID must be unique across the entire repository.

### Issue: "Sensitive file detected"

**Solution**: You may have accidentally committed a large binary file. Use `.pointer.json` files instead. Run:

```bash
python tools/check_sensitive_files.py
```

### Issue: Python dependencies not found

**Solution**: Make sure you've installed dependencies:

```bash
pip install -r tools/requirements.txt
```

## Next Steps

Now that you've created your first record, you can:

1. **Add more artifacts** - Add pointers to audio, video, images, etc.
2. **Configure runtime** - Set up runtime configuration in `runtime/`
3. **Add derived data** - Include embeddings, memory atoms, etc. in `derived/`
4. **Set up inheritance** - Configure inheritance policy in `profile/inheritance_policy.json`
5. **Review policies** - Read through `policies/` to understand compliance requirements

## Additional Resources

- [Architecture Overview](architecture.md)
- [FAQ](FAQ.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Upload Guide](upload-guide.md)
- [Example Records](../examples/)

## Getting Help

If you encounter issues:

- Check the [FAQ](FAQ.md)
- Open an issue on GitHub
- Contact: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions

---

**Congratulations!** 🎉 You've successfully created your first DLRS Hub record.
