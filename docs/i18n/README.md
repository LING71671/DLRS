# Internationalization (i18n) Guide

## Supported Languages

| Language | Code | Status | Maintainer |
|----------|------|--------|------------|
| 简体中文 | zh-CN | ✅ Complete | Core Team |
| English | en-US | ✅ Complete | Core Team |
| 日本語 | ja-JP | 🚧 In Progress | Community |
| 한국어 | ko-KR | 📝 Planned | Community |
| Français | fr-FR | 📝 Planned | Community |
| Deutsch | de-DE | 📝 Planned | Community |
| Español | es-ES | 📝 Planned | Community |

## File Naming Convention

All documentation files should follow this naming pattern:

```
{filename}.{locale}.{extension}
```

Examples:
- `README.md` (default: Chinese)
- `README.en.md` (English)
- `README.ja.md` (Japanese)
- `getting-started.md` (default: Chinese)
- `getting-started.en.md` (English)

## Translation Priority

### High Priority (Core Documentation)
1. README.md
2. docs/getting-started.md
3. docs/FAQ.md
4. CONTRIBUTING.md
5. templates/consent/consent_statement.md

### Medium Priority (Policies)
1. policies/privacy_policy.md
2. policies/takedown_policy.md
3. policies/minor_protection.md
4. policies/deceased_policy.md

### Low Priority (Operations)
1. operations/review_manual.md
2. operations/incident_response.md
3. docs/architecture.md

## Translation Guidelines

### 1. Consistency

Use consistent terminology across all translations:

| English | 简体中文 | 日本語 | 한국어 |
|---------|---------|--------|--------|
| Digital Life | 数字生命 | デジタルライフ | 디지털 라이프 |
| Record | 档案 | レコード | 기록 |
| Consent | 同意 | 同意 | 동의 |
| Pointer | 指针 | ポインタ | 포인터 |
| Artifact | 素材/制品 | アーティファクト | 아티팩트 |
| Manifest | 清单 | マニフェスト | 매니페스트 |
| Badge | 徽章 | バッジ | 배지 |
| Takedown | 下架 | 削除 | 삭제 |
| Withdrawal | 撤回 | 撤回 | 철회 |

### 2. Technical Terms

Keep technical terms in English when appropriate:
- JSON, YAML, Git, GitHub
- API, URI, URL
- SHA256, AES256
- S3, OSS, COS

### 3. Code Examples

Keep code examples and commands in English, but translate comments:

```python
# 简体中文
# 创建新的人类档案
python tools/new_human_record.py --record-id dlrs_12345678

# English
# Create a new human record
python tools/new_human_record.py --record-id dlrs_12345678

# 日本語
# 新しい人間レコードを作成
python tools/new_human_record.py --record-id dlrs_12345678
```

### 4. Legal and Policy Content

⚠️ **Important**: Legal and policy translations must be reviewed by legal professionals in the target jurisdiction. Add this disclaimer to all translated policy documents:

```markdown
> ⚠️ This is a translation for reference only. In case of any discrepancy, 
> the [English/Chinese] version shall prevail. Please consult local legal 
> counsel for compliance in your jurisdiction.
```

## How to Contribute Translations

### Step 1: Check Existing Translations

```bash
# List all files that need translation
find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*"
```

### Step 2: Create Translation File

```bash
# Example: Translate README to Japanese
cp README.md README.ja.md
# Edit README.ja.md with Japanese translation
```

### Step 3: Update Language Switcher

Add language switcher at the top of the document:

```markdown
[English](README.en.md) | [简体中文](README.md) | [日本語](README.ja.md)
```

### Step 4: Submit Pull Request

Use the standard PR template and add `[i18n]` prefix to the title:

```
[i18n] Add Japanese translation for README
```

## Translation Tools

### Recommended Tools
- [DeepL](https://www.deepl.com/) - High-quality machine translation
- [Google Translate](https://translate.google.com/) - Quick reference
- [Crowdin](https://crowdin.com/) - Collaborative translation platform

### Quality Checklist
- [ ] All headings translated
- [ ] All body text translated
- [ ] Code comments translated
- [ ] Technical terms consistent
- [ ] Language switcher added
- [ ] Formatting preserved
- [ ] Links updated (if applicable)
- [ ] Legal disclaimer added (for policy docs)

## Locale-Specific Considerations

### Chinese (zh-CN)
- Use simplified Chinese characters
- Follow Chinese punctuation rules (，。！？)
- Date format: YYYY年MM月DD日
- Use 您 for formal address

### English (en-US)
- Use American English spelling
- Date format: Month DD, YYYY
- Use Oxford comma

### Japanese (ja-JP)
- Use appropriate honorifics (です/ます form)
- Date format: YYYY年MM月DD日
- Mix kanji, hiragana, and katakana appropriately

### Korean (ko-KR)
- Use formal speech level (합니다 form)
- Date format: YYYY년 MM월 DD일
- Use appropriate spacing between words

## Maintenance

### Regular Updates
- When the source document (Chinese or English) is updated, create issues for updating translations
- Use GitHub labels: `i18n`, `translation-needed`, `translation-outdated`

### Version Tracking
Add version information at the top of translated documents:

```markdown
> 📝 Translation Status: Based on v0.2.0 (2026-04-25)  
> 🔄 Last Updated: 2026-04-25  
> 👤 Translator: @username
```

## Contact

For translation questions or to volunteer as a translator:
- Open an issue with `[i18n]` prefix
- Email: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- Join our translation team on Discord

---

Thank you for helping make DLRS Hub accessible to a global audience! 🌍
