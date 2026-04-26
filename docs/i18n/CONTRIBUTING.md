# Contributing Translations to DLRS Hub

Thank you for your interest in helping translate DLRS Hub! This guide will help you get started.

## 🌍 Why Translation Matters

DLRS Hub aims to be a global standard for digital life records. Making documentation accessible in multiple languages helps:

- Reach a wider audience
- Ensure proper understanding of consent and rights
- Support compliance with local regulations
- Build a truly international community

## 🚀 Quick Start

### 1. Check Current Status

```bash
# Install dependencies
pip install -r tools/requirements.txt

# List all supported locales
python tools/i18n_helper.py list

# Check translation status
python tools/i18n_helper.py status

# Find missing translations
python tools/i18n_helper.py check
```

### 2. Choose What to Translate

Priority order:
1. **High Priority**: README.md, getting-started.md, FAQ.md
2. **Medium Priority**: Policy documents (privacy, takedown, etc.)
3. **Low Priority**: Operations manuals, architecture docs

### 3. Create Translation Template

```bash
# Example: Translate README to Japanese
python tools/i18n_helper.py create ja-JP README.md

# This creates README.ja.md with a translation header
```

### 4. Translate the Content

Open the generated file and translate:
- All headings
- All body text
- Code comments (keep commands in English)
- Keep technical terms consistent (see terminology.json)

### 5. Submit Your Translation

```bash
# Add your translation
git add README.ja.md

# Commit with [i18n] prefix
git commit -m "[i18n] Add Japanese translation for README"

# Push and create PR
git push origin your-branch
```

## 📋 Translation Guidelines

### Consistency

Use the terminology defined in `docs/i18n/terminology.json`:

```json
{
  "digital_life": {
    "en-US": "Digital Life",
    "zh-CN": "数字生命",
    "ja-JP": "デジタルライフ"
  }
}
```

### Technical Terms

Keep these in English:
- Git, GitHub, JSON, YAML
- API, URI, URL, HTTP
- SHA256, AES256, KMS
- S3, OSS, COS, MinIO

### Code Examples

Translate comments but keep commands:

```python
# ✅ Good
# 新しい人間レコードを作成
python tools/new_human_record.py --record-id dlrs_12345678

# ❌ Bad (don't translate commands)
python ツール/新しい人間レコード.py --レコードID dlrs_12345678
```

### Legal Content

⚠️ **Important**: Add this disclaimer to all translated policy documents:

```markdown
> ⚠️ This is a translation for reference only. In case of any discrepancy,
> the [English/Chinese] version shall prevail. Please consult local legal
> counsel for compliance in your jurisdiction.
```

### Formatting

Preserve all formatting:
- Markdown headers (`#`, `##`, etc.)
- Lists (ordered and unordered)
- Code blocks with language tags
- Tables
- Links (update if locale-specific versions exist)
- Emoji and badges

### Language Switcher

Add language switcher at the top of each document:

```markdown
**Languages / 语言:** [English](README.en.md) | [简体中文](README.md) | [日本語](README.ja.md)
```

## 🎯 Translation Checklist

Before submitting your PR, verify:

- [ ] All headings translated
- [ ] All body text translated
- [ ] Code comments translated
- [ ] Technical terms consistent with terminology.json
- [ ] Language switcher added/updated
- [ ] Formatting preserved (headers, lists, tables)
- [ ] Links updated (if locale-specific versions exist)
- [ ] Legal disclaimer added (for policy docs)
- [ ] Translation header filled out (date, translator name)
- [ ] No broken links
- [ ] No untranslated sections (except code/commands)

## 🔧 Tools and Resources

### Recommended Translation Tools

- **DeepL** (https://www.deepl.com/) - High-quality machine translation
- **Google Translate** (https://translate.google.com/) - Quick reference
- **Crowdin** (https://crowdin.com/) - Collaborative translation platform

### Quality Assurance

1. **Machine translate first** (DeepL/Google)
2. **Review and refine** (fix terminology, tone, cultural nuances)
3. **Peer review** (ask native speaker to review)
4. **Test links** (ensure all links work)

### Helper Scripts

```bash
# List all markdown files that need translation
find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*"

# Check for broken links (requires markdown-link-check)
npx markdown-link-check README.ja.md

# Count words in a file
wc -w README.md
```

## 🌐 Locale-Specific Guidelines

### Chinese (zh-CN)
- Use simplified characters (简体字)
- Follow Chinese punctuation: ，。！？「」
- Date format: 2026年4月25日
- Use 您 for formal address

### English (en-US)
- Use American spelling (color, not colour)
- Date format: April 25, 2026
- Use Oxford comma in lists

### Japanese (ja-JP)
- Use polite form (です/ます体)
- Date format: 2026年4月25日
- Mix kanji, hiragana, katakana appropriately
- Use 「」 for quotes

### Korean (ko-KR)
- Use formal speech level (합니다체)
- Date format: 2026년 4월 25일
- Proper spacing between words
- Use "" for quotes

### French (fr-FR)
- Use proper accents (é, è, ê, à, etc.)
- Date format: 25/04/2026
- Use « » for quotes
- Follow French typography rules

### German (de-DE)
- Capitalize all nouns
- Date format: 25.04.2026
- Use „" for quotes
- Use ß where appropriate

### Spanish (es-ES)
- Use proper accents (á, é, í, ó, ú, ñ)
- Date format: 25/04/2026
- Use ¿? and ¡! for questions/exclamations
- Use "" for quotes

## 📊 Translation Status Tracking

Add this header to your translation file:

```markdown
<!--
Translation Status: 🚧 In Progress / ✅ Complete / ⚠️ Outdated
Based on: README.md (v0.2.0)
Target Locale: ja-JP (日本語)
Last Updated: 2026-04-25
Translator: @your-github-username
Reviewer: @reviewer-github-username (optional)
-->
```

## 🤝 Getting Help

### Questions?

- Open an issue with `[i18n]` prefix
- Email: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- Join our Discord: https://discord.gg/dlrs-i18n

### Want to Become a Maintainer?

If you're interested in maintaining translations for a specific language:

1. Complete at least 3 high-quality translations
2. Demonstrate consistency and attention to detail
3. Be available to review PRs in your language
4. Contact us at https://github.com/Digital-Life-Repository-Standard/DLRS/discussions

## 📜 License

All translations are subject to the same MIT license as the original content.

By contributing translations, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions help make DLRS Hub accessible to people around the world. Thank you for your time and effort!

---

**Need help?** Don't hesitate to ask! We're here to support you. 💙
