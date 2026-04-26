# 常见问题（FAQ）

**语言 / Languages:** [English](FAQ.en.md) | 简体中文

---

## 一般问题

### 什么是 DLRS Hub？

DLRS Hub（数字生命仓库标准中心）是一个用于管理数字生命档案的标准化系统。它提供了一个框架，用于存储、组织和控制对个人数字表示的访问，包括语音样本、图像、视频和个人数据。

### DLRS Hub 适合谁使用？

DLRS Hub 专为以下人群设计：
- **个人** - 希望保存数字遗产的人
- **家庭** - 管理已故亲人纪念档案的家庭
- **研究人员** - 研究数字身份和 AI 伦理的学者
- **组织** - 构建数字人应用的机构
- **开发者** - 创建 AI 语音/虚拟形象克隆系统的开发者

### DLRS Hub 是免费的吗？

是的，DLRS Hub 是 MIT 许可证下的开源项目。你可以自由使用、修改和分发。

---

## 技术问题

### 为什么不直接把视频放进 GitHub？

**答案**：原始音视频、人脸、声纹和证件属于高敏感数据。GitHub 不适合存储大型二进制文件，因为：

1. **大小限制**：大文件会使 Git 仓库变慢和臃肿
2. **永久历史**：一旦提交，文件很难从 Git 历史中完全删除
3. **隐私风险**：敏感的生物识别数据不应该在公共版本控制中
4. **合规要求**：许多司法管辖区对生物识别数据有特定的安全要求

相反，DLRS Hub 存储**指针文件**（`.pointer.json`），引用安全对象存储（S3、OSS 等）中的数据，同时在 Git 中保留元数据和审计信息。

### 什么是指针文件？

指针文件是一个 JSON 文件，包含存储在其他地方的文件的元数据：

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

这种方法将敏感数据与版本控制分离，同时保持可追溯性。

### 支持哪些对象存储服务？

DLRS Hub 支持任何 S3 兼容的对象存储：
- **AWS S3**（国际）
- **阿里云 OSS**（中国）
- **腾讯云 COS**（中国）
- **Google Cloud Storage**（国际）
- **MinIO**（自托管）
- **Backblaze B2**（国际）

### 如何验证我的档案？

运行验证工具：

```bash
python tools/validate_repo.py
```

这会检查：
- JSON schema 合规性
- 必填字段存在性
- 文件结构正确性
- 敏感文件检测
- 同意文档

---

## 隐私和同意

### 人类档案是否必须公开？

**不是。** 档案**默认是私有的**（`visibility: private`）。公开索引需要：
- 明确授权（`allow_public_listing: true`）
- 已验证同意徽章
- 人工审核批准

你也可以使用 `public_unlisted` 来创建可通过直接链接访问但不可搜索的档案。

### 如何撤回我的同意？

联系你的 `manifest.json` 中指定的端点：

```json
"consent": {
  "withdrawal_endpoint": "mailto:privacy@example.org"
}
```

系统将：
1. **立即冻结**运行态
2. **保留**审计日志（法律要求）
3. **删除**保留期后的个人数据
4. **移除**公开索引

### 未成年人可以创建档案吗？

可以，但有限制：
- 需要监护人同意（`consent.guardian_consent: true`）
- 不能公开索引
- 适用额外的隐私保护
- 必须遵守 COPPA（美国）、GDPR（欧盟）或当地法律

### 已故者的档案如何处理？

已故者的档案需要：
- manifest 中 `status: "deceased"`
- `profile/inheritance_policy.json` 指定继承人
- 执行人联系信息
- 默认操作：冻结档案

---

## 使用和权利

### 数字生命是否等于本人？

**不是。** 这一点非常重要：

- 所有输出都是 **AI 生成或 AI 辅助的内容**
- 它们**不**代表真人的即时真实想法
- 它们是基于训练数据的**模拟**
- 所有输出**必须标记**为 AI 生成

把它看作数字纪念或助手，而不是真人的替代品。

### 我可以商业化使用别人的档案吗？

**只有在明确授权的情况下。** 检查档案的 `manifest.json`：

```json
"rights": {
  "allow_commercial_use": true,  // 必须为 true
  "allow_voice_clone": true,     // 用于语音应用
  "allow_avatar_clone": true     // 用于虚拟形象应用
}
```

未经授权的商业使用是：
- 违反档案许可证
- 可能违法（公开权、人格权）
- 可能被下架和法律诉讼

### 我可以用公开档案做什么？

这取决于授予的权限：

| 权限 | 允许的使用 |
|------|-----------|
| `allow_public_listing` | 在公开索引中查看 |
| `allow_model_finetune` | 训练 AI 模型 |
| `allow_voice_clone` | 创建语音合成 |
| `allow_avatar_clone` | 创建数字虚拟形象 |
| `allow_commercial_use` | 商业应用 |
| `allow_research_use` | 学术研究 |

使用前始终检查特定档案的权限。

### 如何验证档案的真实性？

检查这些指标：

1. **已验证同意徽章**（`review.verified_consent_badge: true`）
2. **来源信息** 在 `audit/provenance.json` 中
3. **同意证据** 在 `consent/` 目录中
4. **审核状态**（`review.status: "approved_public"`）
5. **审计追踪** 在 `audit/access_log.pointer.json` 中

对没有这些验证的档案要谨慎。

---

## 合规和法律

### DLRS Hub 符合 GDPR 吗？

DLRS Hub 提供了 **GDPR 合规的工具和框架**，但是：

⚠️ **你有责任**确保你的具体实施符合 GDPR 和其他法规。

该框架支持：
- 访问权（数据导出）
- 删除权（删除策略）
- 更正权（版本控制）
- 数据可移植性（JSON 格式）
- 同意管理（同意记录）

**建议**：在生产部署前咨询律师。

### CCPA、PIPEDA 或其他隐私法呢？

同样的原则适用：DLRS Hub 提供框架，但你必须确保符合你所在司法管辖区的适用法律。

考虑：
- **美国**：CCPA（加州）、COPPA（儿童）
- **加拿大**：PIPEDA
- **中国**：个人信息保护法（PIPL）
- **日本**：个人信息保护法（APPI）
- **韩国**：个人信息保护法（PIPA）

### 我需要律师吗？

**是的，如果你要在生产环境中部署。** 特别是对于：
- 面向公众的服务
- 商业应用
- 跨境数据传输
- 涉及未成年人的服务
- 纪念/已故者档案

`policies/` 和 `templates/consent/` 中的模板**仅是起点**，不构成法律建议。

---

## 徽章和审核

### 什么是徽章？

徽章表示验证状态：

- 🔵 **verified-consent**：同意已被审核者验证
- 🟢 **public-data-only**：仅包含公开信息（无生物识别）
- 🟡 **research-approved**：批准用于学术研究
- 🔴 **commercial-licensed**：授权商业使用

### 如何获得 verified-consent 徽章？

1. 提交包含完整同意文档的档案
2. 包含同意声明（`consent/consent_statement.md`）
3. 提供同意视频或签名（`consent/consent_video.pointer.json`）
4. 通过自动验证
5. 通过维护者的人工审核
6. 徽章在 `review.verified_consent_badge` 中签发

### 审核流程是什么？

1. **自动验证**：schema、结构、敏感文件
2. **人工审核**：同意验证、内容审核
3. **徽章签发**：已验证徽章添加到 manifest
4. **公开索引**：档案添加到 `registry/humans.index.jsonl`
5. **持续监控**：定期重新验证

---

## 故障排除

### 我的验证失败了。我该怎么办？

1. 仔细阅读错误信息
2. 查看示例档案：`humans/asia/cn/dlrs_94f1c9b8_lin-example/`
3. 验证所有必填字段都存在
4. 确保 JSON 语法有效
5. 运行 `python tools/check_sensitive_files.py`
6. 查看[快速上手指南](getting-started.md)

### 我不小心提交了大文件。如何删除？

```bash
# 从 Git 历史中删除（谨慎使用！）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/large/file" \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送（只有在确定的情况下！）
git push origin --force --all
```

更好的方法：从一开始就使用 `.pointer.json` 文件！

### 如何更新现有档案？

1. 编辑档案目录中的文件
2. 更新 `manifest.json` 中的 `audit.last_modified_at`
3. 运行验证：`python tools/validate_repo.py`
4. 提交并推送更改
5. 如果是公开的，索引将自动更新

---

## 贡献和社区

### 如何贡献？

查看[贡献指南](../CONTRIBUTING.md)了解详情。你可以：
- 添加你自己的档案
- 改进文档
- 修复工具中的 bug
- 翻译到其他语言
- 提出标准改进建议

### 在哪里可以获得帮助？

- **GitHub Issues**：https://github.com/Digital-Life-Repository-Standard/DLRS/issues
- **邮箱**：https://github.com/Digital-Life-Repository-Standard/DLRS/discussions
- **安全问题**：https://github.com/Digital-Life-Repository-Standard/DLRS/security/advisories/new
- **文档**：[docs/](.)

### 我可以在我的项目中使用 DLRS Hub 吗？

可以！DLRS Hub 是开源的（MIT 许可证）。你可以：
- 直接使用
- Fork 并修改
- 在其上构建商业服务
- 贡献改进

只需确保遵守适用的隐私法律。

---

## 高级主题

### `derived/` 和 `artifacts/` 有什么区别？

- **`artifacts/`**：原始源材料（音频、视频、图像）
- **`derived/`**：从制品派生的处理数据（嵌入向量、记忆原子、实体图）

派生数据通常由 AI/ML 管道生成，敏感度低于原始制品。

### 跨境传输如何工作？

检查档案的 `rights.cross_border_transfer_basis`：

- `none`：不允许跨境传输
- `consent`：经明确同意允许
- `contract`：根据合同条款允许
- `adequacy`：允许传输到有充分保护的司法管辖区
- `scc`：根据标准合同条款允许

始终验证是否符合 GDPR 第 44-50 条或等效的当地法律。

### 我可以托管自己的 DLRS Hub 实例吗？

可以！DLRS Hub 设计为可自托管：

1. 克隆仓库
2. 设置对象存储（S3、MinIO 等）
3. 配置访问控制
4. 部署验证工具
5. 设置 CI/CD 进行自动检查

查看[架构](architecture.md)了解部署指导。

---

## 还有问题？

如果你的问题在这里没有得到解答：

1. 查看[完整文档](.)
2. 搜索 [GitHub Issues](https://github.com/Digital-Life-Repository-Standard/DLRS/issues)
3. 使用 `question` 标签开一个新 issue
4. 发邮件给我们：https://github.com/Digital-Life-Repository-Standard/DLRS/discussions

我们在这里帮助你！💙
