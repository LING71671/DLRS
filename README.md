# DLRS Hub：全球数字生命母仓库 - 完整使用指南

<div align="center">

**Digital Life Repository Standard Hub**

一个用于建立"全球数字生命计划"的标准化母仓库

> **📢 This project is currently in RFC stage. Feedback, translations, schema improvements, and ethical review are welcome.**  
> **本项目目前处于 RFC（征求意见）阶段，欢迎反馈、翻译、Schema 改进和伦理审查。**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/CHANGELOG.md)
[![i18n](https://img.shields.io/badge/i18n-2%20languages-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/tree/master/docs/i18n)

**语言 / Languages:** [English](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.en.md) | 简体中文 | [日本語](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.ja.md) 🚧 | [한국어](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.ko.md) 📝

</div>

---

## 📖 目录

- [什么是 DLRS Hub？](#什么是-dlrs-hub)
- [核心概念](#核心概念)
- [快速开始](#快速开始)
- [详细教程](#详细教程)
  - [1. 环境准备](#1-环境准备)
  - [2. 创建你的第一个数字生命档案](#2-创建你的第一个数字生命档案)
  - [3. 填写档案信息](#3-填写档案信息)
  - [4. 校验和提交](#4-校验和提交)
- [目录结构详解](#目录结构详解)
- [常见问题](#常见问题)
- [进阶使用](#进阶使用)
- [贡献指南](#贡献指南)
- [法律声明](#法律声明)

---

## 什么是 DLRS Hub？

DLRS Hub（Digital Life Repository Standard Hub）是一个**数字生命档案标准化管理系统**，旨在建立一个：

- ✅ **可审计**：所有操作都有完整的审计日志
- ✅ **可撤回**：参与者可以随时撤回授权并删除数据
- ✅ **可验证**：通过哈希和签名验证数据完整性
- ✅ **可扩展**：支持多种数据类型和使用场景
- ✅ **隐私优先**：敏感数据不直接存储在 Git 仓库中

### 这个仓库解决什么问题？

DLRS Hub 的目标**不是**把每个人的原始音视频直接塞进 GitHub，而是建立一个安全、合规、可控的数字生命档案体系。

### 五大核心原则

1. **原始敏感素材不直接入 Git**  
   音频、视频、证件、人脸、声纹等高敏感材料存储在区域化对象存储中，本仓库只保存 `.pointer.json` 指针文件、哈希值和审核状态。

2. **自愿参与优先**  
   公开索引只接收本人授权、自愿参与、可撤回的档案。

3. **公开不等于无限使用**  
   每个档案必须明确声明是否允许：公开展示、模型微调、语音克隆、虚拟形象克隆、商业化、跨境处理。

4. **先冻结，后复核，再删除**  
   遇到投诉、冒充、撤回同意、继承争议时，先冻结运行态并保留必要审计证据。

5. **AI 合成必须标识**  
   任何公开输出都必须显式标记为 AI 生成/编辑内容，音视频建议加入水印或 C2PA 内容凭证。

---

## 核心概念

### 三类核心对象

| 对象 | 所在目录 | 作用 |
|------|---------|------|
| **标准** | `standards/dlrs/` | 定义 DLRS 的最低合格规范、目录规范、权限模型、审计模型 |
| **模板** | `templates/` | 供新参与者复制填写，生成自己的数字生命档案 |
| **人类档案** | `humans/{region}/{country}/{record_id_slug}/` | 自愿参与者的档案清单、授权状态、公开资料和指针 |

### 档案可见性级别

- `private`：完全私有，不出现在任何公开索引中
- `public_unlisted`：可通过直接链接访问，但不出现在公开索引中
- `public_indexed`：出现在公开索引中，可被搜索和发现

### 敏感度分级

- `S0_PUBLIC`：公开信息（如公开简介）
- `S1_INTERNAL`：内部信息（如偏好设置）
- `S2_CONFIDENTIAL`：机密信息（如聊天记录）
- `S3_BIOMETRIC`：生物识别信息（如人脸、声纹）
- `S4_IDENTITY`：身份证明文件（如护照、身份证）

---

## 快速开始

### 前置要求

- Git
- Python 3.8+
- 文本编辑器（推荐 VS Code）

### 三步快速体验

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/dlrs-hub.git
cd dlrs-hub

# 2. 安装依赖
pip install -r tools/requirements.txt

# 3. 查看示例档案
cd humans/asia/cn/dlrs_94f1c9b8_lin-example
cat manifest.json
```

---

## 详细教程

### 1. 环境准备

#### 1.1 安装 Python 依赖

```bash
cd dlrs-hub
pip install -r tools/requirements.txt
```

#### 1.2 验证工具可用

```bash
python tools/validate_repo.py --help
python tools/new_human_record.py --help
```

---

### 2. 创建你的第一个数字生命档案

#### 2.1 使用自动化工具创建档案

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "张三" \
  --region asia \
  --country cn
```

这将在 `humans/asia/cn/dlrs_12345678_zhang-san/` 创建一个新档案目录。

#### 2.2 手动创建档案（可选）

如果你想手动创建，可以复制模板：

```bash
# 复制模板到新位置
cp -r templates/archive-types/self-owned/ humans/asia/cn/dlrs_12345678_zhang-san/

# 进入新档案目录
cd humans/asia/cn/dlrs_12345678_zhang-san/
```

---

### 3. 填写档案信息

#### 3.1 编辑 `manifest.json`（核心配置文件）

这是最重要的文件，包含档案的所有元数据。

```json
{
  "schema_version": "0.2.0",
  "record_id": "dlrs_12345678",
  "display_slug": "zhang-san",
  "visibility": "private",  // 可选：private, public_unlisted, public_indexed
  
  "subject": {
    "type": "self",  // self（本人）或 third_party（第三方上传）
    "display_name": "张三",
    "legal_name": null,  // 可选：真实法律姓名
    "locale": "zh-CN",
    "residency_region": "CN",
    "is_minor": false,  // 是否未成年人
    "status": "living"  // living（在世）或 deceased（已故）
  },
  
  "rights": {
    "uploader_role": "self",
    "rights_basis": ["consent"],  // 权利基础：consent, contract, legitimate_interest
    "evidence_refs": [
      "consent/consent_statement.md",
      "consent/consent_video.pointer.json"
    ],
    "allow_public_listing": false,  // 是否允许公开索引
    "allow_commercial_use": false,  // 是否允许商业使用
    "allow_model_finetune": false,  // 是否允许模型微调
    "allow_voice_clone": false,     // 是否允许语音克隆
    "allow_avatar_clone": false,    // 是否允许虚拟形象克隆
    "allow_research_use": false,    // 是否允许研究使用
    "cross_border_transfer_basis": "none",
    "cross_border_transfer_status": "not_needed"
  },
  
  "consent": {
    "captured_at": "2026-04-25T10:30:00+08:00",
    "withdrawal_endpoint": "mailto:your-email@example.com",  // 撤回联系方式
    "separate_biometric_consent": true,
    "guardian_consent": false,
    "consent_version": "0.2.0",
    "allowed_scopes": [
      "storage",
      "structured_processing"
    ]
  },
  
  "artifacts": [],  // 稍后填写
  
  "deletion_policy": {
    "allow_delete": true,
    "allow_export": true,
    "withdrawal_effect": "freeze_runtime_then_delete",
    "legal_hold": false
  },
  
  "security": {
    "primary_region": "CN",
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
    "created_at": "2026-04-25T10:45:00+08:00",
    "last_modified_at": "2026-04-25T10:45:00+08:00",
    "change_log_hash": null
  }
}
```

#### 3.2 编辑 `public_profile.json`（公开简介）

如果你计划公开档案，需要填写这个文件：

```json
{
  "display_name": "张三",
  "bio": "一个热爱技术的开发者",
  "avatar_url": null,
  "social_links": {
    "github": "https://github.com/zhangsan",
    "twitter": null,
    "website": "https://zhangsan.example.com"
  },
  "tags": ["developer", "ai", "open-source"],
  "locale": "zh-CN"
}
```

#### 3.3 填写同意声明 `consent/consent_statement.md`

```markdown
# 数字生命档案同意声明

我，张三，确认：

1. 我自愿参与 DLRS 数字生命计划
2. 我理解我的数据将如何被使用
3. 我保留随时撤回授权的权利

签署日期：2026-04-25
签署人：张三
```

#### 3.4 添加数据指针（不上传原始文件！）

在 `artifacts/raw_pointers/` 目录下创建指针文件，例如 `audio/voice_master.pointer.json`：

```json
{
  "artifact_id": "voice_001",
  "type": "voice_sample",
  "format": "wav",
  "storage_uri": "s3://my-bucket/audio/voice_master.wav",
  "checksum": "sha256:abc123...",
  "size_bytes": 1048576,
  "region": "CN",
  "sensitivity": "S3_BIOMETRIC",
  "contains_sensitive_data": true,
  "created_at": "2026-04-25T10:00:00+08:00"
}
```

同时在 `manifest.json` 的 `artifacts` 数组中添加引用：

```json
"artifacts": [
  {
    "artifact_id": "voice_001",
    "type": "voice_sample",
    "format": "wav",
    "storage_uri": "s3://my-bucket/audio/voice_master.wav",
    "checksum": "sha256:abc123...",
    "region": "CN",
    "sensitivity": "S3_BIOMETRIC",
    "contains_sensitive_data": true
  }
]
```

---

### 4. 校验和提交

#### 4.1 本地校验

```bash
# 回到仓库根目录
cd /path/to/dlrs-hub

# 运行校验工具
python tools/validate_repo.py

# 如果通过，会显示：
# ✓ All validations passed
```

#### 4.2 生成索引（如果是公开档案）

```bash
python tools/build_registry.py
```

这会更新 `registry/humans.index.jsonl` 文件。

#### 4.3 提交到 Git

```bash
git add humans/asia/cn/dlrs_12345678_zhang-san/
git commit -m "Add: 张三的数字生命档案"
git push
```

#### 4.4 创建 Pull Request

如果你是向公共仓库贡献，需要创建 PR：

1. 在 GitHub 上点击 "New Pull Request"
2. 选择模板：`.github/PULL_REQUEST_TEMPLATE/human-record.md`
3. 填写 PR 描述
4. 等待审核

---

## 目录结构详解

```text
dlrs-hub/
│
├── standards/              # 📜 DLRS 标准文档
│   └── dlrs/
│       ├── v0.2/          # 版本化标准
│       └── README.md
│
├── schemas/               # 🔍 JSON Schema 验证规则
│   ├── manifest.schema.json
│   ├── public_profile.schema.json
│   └── pointer.schema.json
│
├── registry/              # 📇 公开索引
│   ├── humans.index.jsonl      # 所有公开档案的索引
│   ├── badges.index.json       # 徽章系统
│   └── regions/               # 按地区分类的索引
│
├── humans/                # 👤 人类档案目录
│   ├── asia/
│   │   └── cn/
│   │       └── dlrs_12345678_zhang-san/
│   │           ├── manifest.json           # 核心配置
│   │           ├── public_profile.json     # 公开简介
│   │           ├── README.md              # 档案说明
│   │           ├── consent/               # 同意证据
│   │           │   ├── consent_statement.md
│   │           │   └── consent_video.pointer.json
│   │           ├── profile/               # 个人资料
│   │           │   ├── subject_profile.json
│   │           │   ├── values_and_preferences.json
│   │           │   ├── relationship_policy.json
│   │           │   └── inheritance_policy.json
│   │           ├── artifacts/             # 数据指针
│   │           │   ├── raw_pointers/
│   │           │   │   ├── audio/
│   │           │   │   ├── video/
│   │           │   │   ├── image/
│   │           │   │   ├── text/
│   │           │   │   └── avatar/
│   │           │   └── samples/          # 小样本（可选）
│   │           ├── derived/              # 派生数据
│   │           │   ├── embeddings.pointer.json
│   │           │   ├── memory_atoms.jsonl
│   │           │   ├── entity_graph.jsonl
│   │           │   └── moderation_report.json
│   │           ├── runtime/              # 运行时配置
│   │           │   ├── build_spec.json
│   │           │   ├── adapters.pointer.json
│   │           │   ├── session_policies.json
│   │           │   └── prompts/
│   │           │       └── system.md
│   │           └── audit/                # 审计日志
│   │               ├── provenance.json
│   │               ├── access_log.pointer.json
│   │               └── takedown_log.jsonl
│   ├── europe/
│   ├── americas/
│   └── _TEMPLATE/         # 档案模板
│
├── templates/             # 📋 各类模板
│   ├── archive-types/
│   │   ├── self-owned/    # 本人上传模板
│   │   ├── memorial/      # 纪念档案模板
│   │   └── research/      # 研究用途模板
│   ├── consent/           # 同意书模板
│   └── pr-packages/       # PR 提交包模板
│
├── examples/              # 💡 示例档案（虚构数据）
│   ├── minimal-private/
│   ├── public-indexed-demo/
│   └── memorial-estate-demo/
│
├── tools/                 # 🛠️ 自动化工具
│   ├── validate_repo.py          # 校验工具
│   ├── build_registry.py         # 索引生成工具
│   ├── new_human_record.py       # 新建档案工具
│   ├── check_sensitive_files.py  # 敏感文件检查
│   └── requirements.txt
│
├── policies/              # 📋 政策文档
│   ├── privacy_policy.md
│   ├── takedown_policy.md
│   ├── minor_protection.md
│   ├── deceased_policy.md
│   └── cross_border.md
│
├── operations/            # 🔧 运营手册
│   ├── review_manual.md
│   ├── incident_response.md
│   ├── badge_issuance.md
│   └── sla.md
│
├── api/                   # 🌐 API 规范
│   ├── openapi.yaml
│   └── websocket-events.md
│
├── docs/                  # 📚 文档
│   ├── getting-started.md
│   ├── architecture.md
│   ├── FAQ.md
│   ├── upload-guide.md
│   └── references.md
│
└── .github/               # ⚙️ GitHub 配置
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE/
    └── workflows/
```

---

## 常见问题

### Q1: 为什么不直接把视频放进 GitHub？

**A:** 因为原始音视频、人脸、声纹和证件属于高敏感数据。GitHub 不适合存储大型二进制文件，且一旦提交就难以完全删除。母仓库应该保存指针和审计信息，而不是直接托管原件。

### Q2: 人类档案是否必须公开？

**A:** 不是。默认是私有的（`visibility: private`）。公开索引需要额外授权和审核。

### Q3: 数字生命是否等于本人？

**A:** 不是。所有输出都只是 AI 生成或辅助生成内容，不代表真人的即时真实意思表示。必须明确标识为 AI 生成内容。

### Q4: 如何撤回我的档案？

**A:** 联系 `manifest.json` 中 `consent.withdrawal_endpoint` 指定的邮箱或端点。系统会先冻结运行态，然后删除数据。

### Q5: 未成年人可以创建档案吗？

**A:** 可以，但必须有监护人同意（`consent.guardian_consent: true`），且不能公开索引。

### Q6: 已故者的档案如何处理？

**A:** 必须有 `profile/inheritance_policy.json` 指定继承人和处理方式。默认行为是冻结档案。

### Q7: 我可以商业化使用别人的档案吗？

**A:** 必须检查该档案的 `rights.allow_commercial_use` 字段。未经授权的商业使用是违法的。

### Q8: 如何验证档案的真实性？

**A:** 检查 `review.verified_consent_badge` 徽章，以及 `audit/provenance.json` 中的来源证明。

---

## 进阶使用

### 公开索引准入条件

一个档案要进入 `registry/humans.index.jsonl`，必须满足：

- ✅ `review.status = approved_public`
- ✅ `visibility = public_indexed` 或 `public_unlisted`
- ✅ `review.verified_consent_badge = true` 或 `review.public_data_only_badge = true`
- ✅ `rights.allow_public_listing = true`
- ✅ `consent.withdrawal_endpoint` 非空
- ✅ 未成年人档案不得公开索引
- ✅ 逝者档案必须有 `profile/inheritance_policy.json`

### 徽章系统

DLRS Hub 提供以下徽章：

- 🔵 **verified-consent**：已验证同意
- 🟢 **public-data-only**：仅公开数据
- 🟡 **research-approved**：研究用途批准
- 🔴 **commercial-licensed**：商业授权

### 审核流程

1. 提交 PR
2. 自动校验（CI）
3. 人工审核
4. 签发徽章
5. 合并到主分支
6. 更新公开索引

### 对象存储配置

推荐使用：

- 中国大陆：[阿里云 OSS](https://www.aliyun.com/product/oss)、[腾讯云 COS](https://cloud.tencent.com/product/cos)
- 国际：[AWS S3](https://aws.amazon.com/s3/)、[Google Cloud Storage](https://cloud.google.com/storage)
- 私有部署：[MinIO](https://min.io/)

配置示例：

```json
{
  "storage_uri": "s3://my-bucket/path/to/file.wav",
  "region": "cn-shanghai",
  "encryption": "AES256",
  "access_control": "private"
}
```

---

## 贡献指南

我们欢迎以下类型的贡献：

### 1. 标准改进

使用 Issue 模板：`spec_proposal`

### 2. 新增人类档案

使用 PR 模板：`human-record`

### 3. 工具和 Schema 修复

普通 Pull Request

### 4. 投诉和下架请求

使用 Issue 模板：`takedown`，或发送到安全邮箱

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/your-org/dlrs-hub.git
cd dlrs-hub

# 安装依赖
pip install -r tools/requirements.txt

# 运行测试
python tools/validate_repo.py
python tools/check_sensitive_files.py

# 生成索引
python tools/build_registry.py
```

---

## 法律声明

⚠️ **重要提醒**

本项目涉及：

- 肖像权和声音权
- 生物识别信息
- 个人信息保护
- 逝者权益
- 跨境数据传输
- AI 合成内容标识
- 深度伪造滥用风险

**正式上线前必须由目标法域的律师审核以下内容：**

- `policies/` 目录下的所有政策
- `templates/consent/` 目录下的同意书模板
- `LEGAL_DISCLAIMER.md`

**免责声明：**

本仓库提供的模板和工具仅供参考，不构成法律建议。使用者需自行承担合规责任。

---

## 版本信息

- 当前版本：**v0.2.0**
- 发布日期：2026-04-25
- 状态：草案阶段

查看完整更新日志：[CHANGELOG.md](CHANGELOG.md)

---

## 相关资源

- 📖 [完整文档](docs/)
- 🗺️ [项目路线图](ROADMAP.md) - 长期规划和版本计划
- 🎯 [实施状态](docs/IMPLEMENTATION_STATUS.md) - 当前完成度总结
- 📊 [差距分析](docs/GAP_ANALYSIS.md) - 与终极标准的详细对比
- 🚀 [终极标准](DLRS_ULTIMATE.md) - 完整的行业标准草案
- 🏗️ [架构设计](docs/architecture.md)
- ❓ [常见问题](docs/FAQ.md)
- 🤝 [贡献指南](CONTRIBUTING.md)
- 🌍 [国际化 (i18n)](docs/i18n/) - 翻译指南和多语言支持
- 📜 [行为准则](CODE_OF_CONDUCT.md)
- 🏛️ [治理模型](GOVERNANCE.md)

---

## 联系方式

- 问题反馈：[GitHub Issues](https://github.com/your-org/dlrs-hub/issues)
- 安全问题：security@example.org
- 一般咨询：contact@example.org

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**让数字生命更安全、更透明、更可控**

Made with ❤️ by DLRS Community

</div>
