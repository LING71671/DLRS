# Digital Life Repository Standard (DLRS) v0.5 Draft

<div align="center">

**DLRS 是一个面向数字生命档案的开放标准草案**  
**重点解决隐私优先、自愿授权、结构化存档、可撤回、可审计、Schema 校验和模板化提交等问题**

> **📢 RFC Stage | 征求意见阶段**  
> This is an early-stage open standard draft. Feedback, translations, schema improvements, and ethical review are welcome.  
> 这是早期开放标准草案。欢迎反馈、翻译、Schema 改进和伦理审查。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/LICENSE)
[![Version](https://img.shields.io/badge/version-v0.5%20Draft-orange.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/CHANGELOG.md)
[![i18n](https://img.shields.io/badge/i18n-2%20languages-blue.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/tree/master/docs/i18n)
[![RFC](https://img.shields.io/badge/RFC-Open%20for%20Comment-green.svg)](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/docs/community/RFC-DLRS-v0.2.md)

**语言 / Languages:** [English](https://github.com/Digital-Life-Repository-Standard/DLRS/blob/master/README.en.md) | 简体中文

</div>

---

## 🎯 什么是 DLRS？

**DLRS (Digital Life Repository Standard)** 是一个**开放标准草案**，用于隐私优先、基于授权的数字生命档案。

它定义了：
- 📋 档案目录结构和 JSON Schema
- ✅ 授权和撤回模型
- 🔒 隐私边界和敏感度分级
- 🏛️ 治理规则和审核流程
- 🛠️ 验证工具和档案模板
- ⚖️ 法律免责声明和伦理指南

---

## ❌ DLRS 不是什么

**重要声明**：

- ❌ **不是**"复活人类"或"克隆人格"的技术
- ❌ **不是**保证 AI 分身等同真人的承诺
- ❌ **不是**法律合规的保证
- ❌ **不是**永久存储解决方案
- ❌ **不是**成熟的生产系统
- ❌ **不是**法律建议的替代品

---

## ✅ DLRS 是什么

- ✅ **开放标准草案**：用于讨论和改进
- ✅ **隐私优先**：敏感数据不直接存储在 Git
- ✅ **基于授权**：所有档案必须有明确授权证据
- ✅ **可撤回**：用户可以随时撤回授权
- ✅ **可审计**：所有操作都有审计日志
- ✅ **实验性**：非约束性参考实现
- ✅ **社区驱动**：欢迎贡献和反馈

---

## 🚀 为什么需要 DLRS？

随着 AI 技术的发展，数字生命档案（digital life archives）变得越来越重要。但目前缺少：

1. **标准化的档案结构** - 每个项目都在重新发明轮子
2. **明确的授权模型** - 如何证明用户同意？如何撤回？
3. **隐私保护框架** - 哪些数据不应直接存储？如何安全引用？
4. **治理和审核规则** - 如何处理争议？如何验证真实性？
5. **伦理边界定义** - 即使有授权，哪些行为也应被禁止？

DLRS 试图通过开放标准的方式解决这些问题。

---

## 📖 核心概念

### 三层架构

```
Git 仓库（公开/私有）
├── manifest.json          # 元数据和配置
├── consent/               # 授权证据（可使用指针）
├── artifacts/raw_pointers/ # 指针文件（不存储原始数据）
└── audit/                 # 审计日志

外部存储（加密、访问控制）
├── s3://bucket/voice/master.wav
├── s3://bucket/video/training.mp4
└── s3://bucket/images/headshot.jpg
```

### 敏感度分级

- `S0_PUBLIC` - 公开信息（如公开简介）
- `S1_INTERNAL` - 内部信息（如偏好设置）
- `S2_CONFIDENTIAL` - 机密信息（如聊天记录）
- `S3_BIOMETRIC` - 生物识别信息（如人脸、声纹）
- `S4_IDENTITY` - 身份证明文件（如护照、身份证）

### 可见性级别

- `private` - 完全私有
- `public_unlisted` - 可通过直接链接访问
- `public_indexed` - 可被搜索和发现

---

## 🏁 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Digital-Life-Repository-Standard/DLRS.git
cd DLRS
```

### 2. 安装依赖

```bash
pip install -r tools/requirements.txt
```

### 3. 查看示例档案

```bash
cd examples/minimal-private
cat manifest.json
```

### 4. 创建你的第一个档案

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "张三" \
  --region asia \
  --country cn
```

### 5. 验证档案

```bash
python tools/validate_repo.py
```

---

## 📚 文档

- 📖 [完整使用指南](docs/getting-started.md)
- 🤔 [常见问题](docs/FAQ.md)
- 🏗️ [架构设计](docs/architecture.md)
- 📋 [RFC: DLRS v0.2](docs/community/RFC-DLRS-v0.2.md)
- 💬 [授权模型反馈](docs/community/consent-model-feedback.md)
- 🎯 [Good First Issues](docs/community/good-first-issues.md)
- 📢 [社区推广指南](docs/community/community-promotion-guide.md)

---

## 🤝 如何贡献

我们欢迎以下类型的贡献：

1. **反馈和建议** - 提交 Issue 或参与 Discussions
2. **文档改进** - 修正错误、添加示例、翻译文档
3. **Schema 改进** - 优化 JSON Schema 设计
4. **工具开发** - 改进验证工具、添加新功能
5. **示例档案** - 提供更多模板和示例
6. **伦理审查** - 指出潜在的伦理和法律风险

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 🌍 国际化

当前支持语言：
- 🇨🇳 简体中文
- 🇺🇸 English

欢迎贡献更多语言翻译！见 [i18n 指南](docs/i18n/)

---

## 📊 当前状态

**版本**: v0.5 Draft  
**状态**: RFC（征求意见）阶段  
**完成度**: 约 83% (v0.5 release)

### ✅ 已完成
- 基础目录结构
- JSON Schema 定义
- 授权和撤回模型
- 隐私边界定义
- 验证工具
- 示例档案
- 中英文文档

### 🚧 进行中
- 社区反馈收集
- Schema 优化
- 文档完善
- 多语言翻译

### 📋 计划中
- 媒体采集规范
- 构建管线
- 运行时系统
- 权限和审计实现

详见 [ROADMAP.md](ROADMAP.md) 和 [实施状态](docs/IMPLEMENTATION_STATUS.md)

---

## ⚖️ 法律和伦理

**重要提醒**：

本项目涉及：
- 肖像权和声音权
- 生物识别信息
- 个人信息保护
- 逝者权益
- 跨境数据传输
- AI 合成内容标识
- 深度伪造滥用风险

**免责声明**：
- 本仓库提供的模板和工具仅供参考，不构成法律建议
- 使用者需自行承担合规责任
- 正式使用前必须咨询法律专业人士

详见 [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md)

---

## 📞 联系方式

- 💬 [GitHub Discussions](https://github.com/Digital-Life-Repository-Standard/DLRS/discussions)
- 🐛 [Issues](https://github.com/Digital-Life-Repository-Standard/DLRS/issues)
- 📧 安全问题：见 [SECURITY.md](SECURITY.md)

---

## 📄 许可证

本项目采用 [MIT License](LICENSE)。

---

## 🙏 致谢

感谢所有贡献者和社区成员的支持！

---

## 🔗 相关资源

- [完整标准草案](DLRS_ULTIMATE.md)
- [差距分析](docs/GAP_ANALYSIS.md)
- [实施状态](docs/IMPLEMENTATION_STATUS.md)
- [项目路线图](ROADMAP.md)
- [治理模型](GOVERNANCE.md)
- [行为准则](CODE_OF_CONDUCT.md)

---

<div align="center">

**让数字生命档案更安全、更透明、更可控**

Made with ❤️ by DLRS Community

</div>
