# RFC: DLRS v0.2 – Digital Life Repository Standard

**Status**: Open for Comment  
**Version**: DLRS v0.2 Draft  
**Last Updated**: 2026-04-26

---

## English Version

### What is DLRS v0.2?

DLRS (Digital Life Repository Standard) v0.2 is an **early-stage open standard draft** for privacy-first, consent-based digital life archives. It defines:

- Archive directory structure
- JSON schemas for manifests, consent records, and pointers
- Consent and withdrawal models
- Privacy boundaries and sensitivity levels
- Governance rules and review processes
- Validation tools and templates
- Legal disclaimers and ethical guidelines

**DLRS is NOT**:
- A guarantee of legal compliance
- A promise to "resurrect" or "clone" a person
- A claim that AI avatars equal real humans
- A permanent storage solution
- A replacement for legal advice

**DLRS IS**:
- An open standard draft for discussion
- A template and schema collection
- A consent-based archival framework
- A privacy-first approach to digital legacy
- An experimental, non-binding reference

---

### We Welcome Feedback On

#### 1. **Archive Directory Structure**
- Is the `humans/{region}/{country}/{record_id}/` structure appropriate?
- Should we support team/organization archives differently?
- How should we handle multi-regional data?

#### 2. **Consent and Withdrawal Model**
- Is the consent evidence structure sufficient?
- How should withdrawal requests be processed?
- Should there be a grace period before deletion?
- How should we handle deceased persons' archives?

#### 3. **Privacy Boundaries**
- What data should **never** be stored directly in Git?
- Are the sensitivity levels (S0-S4) appropriate?
- Should biometric data always use pointer files?
- How should we handle AI-generated content?

#### 4. **JSON Schema Design**
- Are the required fields appropriate?
- Should we add more validation rules?
- How should we version schemas?
- Are field names clear and consistent?

#### 5. **Governance Rules**
- Is the review process clear?
- Should there be different tiers of verification?
- How should we handle disputes?
- What should the badge system look like?

#### 6. **Legal and Ethical Risks**
- Are the disclaimers sufficient?
- What risks are we missing?
- How should we handle cross-border data transfers?
- What should be forbidden even with consent?

#### 7. **Validation Tools**
- Are the Python validation scripts helpful?
- What additional checks are needed?
- Should we support other languages?
- How can we make error messages clearer?

#### 8. **Internationalization**
- Are translations accurate?
- What languages should we prioritize?
- How should we handle region-specific requirements?
- Are terminology choices appropriate?

#### 9. **Example Archives**
- Are the example archives helpful?
- What additional examples are needed?
- Should we provide more templates?
- How can we make examples clearer?

---

### How to Provide Feedback

1. **Open an Issue**: Use the "RFC Feedback" issue template
2. **Start a Discussion**: Use GitHub Discussions (if enabled)
3. **Submit a Pull Request**: Propose specific changes
4. **Email**: Contact the maintainers directly (see SECURITY.md)

---

### Key Principles

- **Privacy First**: Sensitive data should not be stored directly in Git
- **Consent Based**: All archives must have clear consent evidence
- **Revocable**: Users must be able to withdraw consent
- **Auditable**: All actions must be logged
- **Transparent**: AI-generated content must be clearly marked
- **Non-Binding**: This is a draft standard, not legal advice

---

### What Should Never Be Stored Directly in Git

❌ **Never store these directly**:
- Raw biometric data (fingerprints, iris scans, DNA)
- High-resolution face images (use pointers)
- Raw voice recordings (use pointers)
- Identity documents (passports, IDs)
- Medical records
- Financial information
- Private keys or passwords

✅ **Use pointer files instead**:
- Store metadata and checksums in Git
- Store actual files in encrypted object storage
- Reference external storage URIs
- Include access control information

---

### Recommended Approach

```
Git Repository (Public/Private)
├── manifest.json (metadata only)
├── consent/ (consent evidence, may use pointers)
├── artifacts/raw_pointers/ (pointer files only)
└── audit/ (audit logs, may use pointers)

External Storage (Encrypted, Access-Controlled)
├── s3://bucket/voice/master.wav
├── s3://bucket/video/training.mp4
└── s3://bucket/images/headshot.jpg
```

---

## 中文版本

### DLRS v0.2 是什么？

DLRS（数字生命仓库标准）v0.2 是一个**早期开放标准草案**，用于隐私优先、基于授权的数字生命档案。它定义了：

- 档案目录结构
- 清单、授权记录和指针的 JSON Schema
- 授权和撤回模型
- 隐私边界和敏感度分级
- 治理规则和审核流程
- 验证工具和模板
- 法律免责声明和伦理指南

**DLRS 不是**：
- 法律合规的保证
- "复活"或"克隆"人类的承诺
- AI 分身等同真人的声明
- 永久存储解决方案
- 法律建议的替代品

**DLRS 是**：
- 用于讨论的开放标准草案
- 模板和 Schema 集合
- 基于授权的归档框架
- 隐私优先的数字遗产方法
- 实验性、非约束性参考

---

### 我们欢迎以下方面的反馈

#### 1. **档案目录结构**
- `humans/{region}/{country}/{record_id}/` 结构是否合适？
- 是否应该以不同方式支持团队/组织档案？
- 如何处理多区域数据？

#### 2. **授权和撤回模型**
- 授权证据结构是否充分？
- 撤回请求应如何处理？
- 删除前是否应有宽限期？
- 如何处理已故者的档案？

#### 3. **隐私边界**
- 哪些数据**绝不**应直接存储在 Git 中？
- 敏感度分级（S0-S4）是否合适？
- 生物识别数据是否应始终使用指针文件？
- 如何处理 AI 生成的内容？

#### 4. **JSON Schema 设计**
- 必填字段是否合适？
- 是否应添加更多验证规则？
- Schema 应如何版本化？
- 字段名称是否清晰一致？

#### 5. **治理规则**
- 审核流程是否清晰？
- 是否应有不同层级的验证？
- 如何处理争议？
- 徽章系统应该是什么样的？

#### 6. **法律和伦理风险**
- 免责声明是否充分？
- 我们遗漏了哪些风险？
- 如何处理跨境数据传输？
- 即使有授权，哪些行为也应被禁止？

#### 7. **验证工具**
- Python 验证脚本是否有帮助？
- 需要哪些额外检查？
- 是否应支持其他语言？
- 如何使错误消息更清晰？

#### 8. **国际化**
- 翻译是否准确？
- 应优先考虑哪些语言？
- 如何处理特定区域的要求？
- 术语选择是否合适？

#### 9. **示例档案**
- 示例档案是否有帮助？
- 需要哪些额外示例？
- 是否应提供更多模板？
- 如何使示例更清晰？

---

### 如何提供反馈

1. **提交 Issue**：使用"RFC 反馈"Issue 模板
2. **发起讨论**：使用 GitHub Discussions（如果启用）
3. **提交 Pull Request**：提出具体更改
4. **邮件**：直接联系维护者（见 SECURITY.md）

---

### 核心原则

- **隐私优先**：敏感数据不应直接存储在 Git 中
- **基于授权**：所有档案必须有明确的授权证据
- **可撤回**：用户必须能够撤回授权
- **可审计**：所有操作必须记录
- **透明**：AI 生成的内容必须明确标记
- **非约束性**：这是标准草案，不是法律建议

---

### 哪些内容绝不应直接存储在 Git 中

❌ **绝不直接存储**：
- 原始生物识别数据（指纹、虹膜扫描、DNA）
- 高分辨率人脸图像（使用指针）
- 原始语音录音（使用指针）
- 身份证明文件（护照、身份证）
- 医疗记录
- 财务信息
- 私钥或密码

✅ **改用指针文件**：
- 在 Git 中存储元数据和校验和
- 在加密对象存储中存储实际文件
- 引用外部存储 URI
- 包含访问控制信息

---

### 推荐方法

```
Git 仓库（公开/私有）
├── manifest.json（仅元数据）
├── consent/（授权证据，可使用指针）
├── artifacts/raw_pointers/（仅指针文件）
└── audit/（审计日志，可使用指针）

外部存储（加密、访问控制）
├── s3://bucket/voice/master.wav
├── s3://bucket/video/training.mp4
└── s3://bucket/images/headshot.jpg
```

---

## Version History

- **v0.1** (Initial public draft): Basic structure and concepts
- **v0.2** (Current): Template, schema, consent, disclaimer, governance and validation structure draft

---

## License

This RFC document is part of the DLRS project and is licensed under MIT License.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.
