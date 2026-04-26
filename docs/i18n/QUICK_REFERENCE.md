# i18n Quick Reference Card

## 🚀 Quick Commands

```bash
# List all locales
python tools/i18n_helper.py list

# Check translation status
python tools/i18n_helper.py status

# Find missing translations
python tools/i18n_helper.py check

# Create translation template
python tools/i18n_helper.py create <locale> <file>
```

## 🌍 Locale Codes

| Code | Language | Native | Status |
|------|----------|--------|--------|
| zh-CN | Chinese | 简体中文 | ✅ |
| en-US | English | English | ✅ |
| ja-JP | Japanese | 日本語 | 🚧 |
| ko-KR | Korean | 한국어 | 📝 |
| fr-FR | French | Français | 📝 |
| de-DE | German | Deutsch | 📝 |
| es-ES | Spanish | Español | 📝 |

## 📝 File Naming

```
{filename}.{locale}.{extension}

Examples:
- README.md (default)
- README.en.md
- README.ja.md
- getting-started.en.md
```

## 🎯 Key Terms

| English | 中文 | 日本語 | 한국어 |
|---------|------|--------|--------|
| Digital Life | 数字生命 | デジタルライフ | 디지털 라이프 |
| Record | 档案 | レコード | 기록 |
| Consent | 同意 | 同意 | 동의 |
| Pointer | 指针 | ポインタ | 포인터 |
| Manifest | 清单 | マニフェスト | 매니페스트 |
| Badge | 徽章 | バッジ | 배지 |

## ✅ Translation Checklist

- [ ] All headings translated
- [ ] All body text translated
- [ ] Code comments translated
- [ ] Technical terms consistent
- [ ] Language switcher added
- [ ] Formatting preserved
- [ ] Links updated
- [ ] Legal disclaimer (if policy doc)
- [ ] Translation header filled

## 📋 Translation Header Template

```markdown
<!--
Translation Status: 🚧 In Progress
Based on: {source_file} (v0.2.0)
Target Locale: {locale} ({native_name})
Last Updated: YYYY-MM-DD
Translator: @your-username
-->
```

## 🔗 Important Links

- [Full i18n Guide](README.md)
- [Contribution Guide](CONTRIBUTING.md)
- [Terminology](terminology.json)
- [Locale Config](locales.yaml)

## 💡 Tips

1. **Use DeepL** for initial translation
2. **Check terminology.json** for consistency
3. **Keep code/commands in English**
4. **Add legal disclaimer** for policy docs
5. **Test all links** before submitting

## 🆘 Need Help?

- Email: https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- GitHub: Use `[i18n]` label
- Discord: https://discord.gg/dlrs-i18n
