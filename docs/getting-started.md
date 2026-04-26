# 快速上手指南

**语言 / Languages:** [English](getting-started.en.md) | 简体中文

---

本指南将帮助你设置 DLRS Hub 并创建你的第一个数字生命档案。

## 前置要求

开始之前，请确保你已安装：

- **Git** - 版本控制系统
- **Python 3.8+** - Python 运行环境
- **文本编辑器** - 如 VS Code、Sublime Text 等
- 基本的命令行使用知识

## 第一步：设置仓库

### 克隆或初始化

如果你是从零开始：

```bash
# 初始化新的 Git 仓库
git init DLRS
cd DLRS

# 或者克隆现有仓库
git clone https://github.com/Digital-Life-Repository-Standard/DLRS.git
cd DLRS
```

### 安装依赖

```bash
# 安装 Python 依赖
pip install -r tools/requirements.txt

# 验证安装
python tools/validate_repo.py --help
```

你应该能看到验证工具的帮助信息。

## 第二步：创建你的第一个人类档案

### 方式 A：使用自动化工具（推荐）

最简单的方式是使用 `new_human_record.py` 工具：

```bash
python tools/new_human_record.py \
  --record-id dlrs_12345678 \
  --display-name "张三" \
  --region asia \
  --country cn
```

**参数说明：**
- `--record-id`：唯一标识符（格式：`dlrs_` + 8个字符）
- `--display-name`：显示名称
- `--region`：地理区域（asia、europe、americas、africa、oceania）
- `--country`：国家代码（ISO 3166-1 alpha-2，如 cn、us、jp）

这将在以下位置创建新的目录结构：
```
humans/asia/cn/dlrs_12345678_zhang-san/
```

### 方式 B：手动创建

如果你喜欢手动设置：

```bash
# 复制模板
cp -r humans/_TEMPLATE/ humans/asia/cn/dlrs_12345678_zhang-san/

# 进入新目录
cd humans/asia/cn/dlrs_12345678_zhang-san/
```

## 第三步：填写档案信息

### 编辑 manifest.json

这是核心配置文件。打开 `manifest.json` 并更新：

```json
{
  "schema_version": "0.2.0",
  "record_id": "dlrs_12345678",
  "display_slug": "zhang-san",
  "visibility": "private",
  
  "subject": {
    "type": "self",
    "display_name": "张三",
    "locale": "zh-CN",
    "residency_region": "CN",
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
    "captured_at": "2026-04-25T10:30:00+08:00",
    "withdrawal_endpoint": "mailto:your-email@example.com"
  }
}
```

### 编辑 public_profile.json（可选）

如果你计划公开档案：

```json
{
  "display_name": "张三",
  "bio": "一个热爱技术的开发者",
  "locale": "zh-CN",
  "tags": ["developer", "ai", "open-source"]
}
```

### 添加同意声明

编辑 `consent/consent_statement.md`：

```markdown
# 数字生命档案同意声明

我，张三，确认：

1. 我自愿参与 DLRS 数字生命计划
2. 我理解我的数据将如何被使用
3. 我保留随时撤回授权的权利

签署日期：2026年4月25日
签署人：张三
```

### 添加数据指针（不要上传原始文件！）

⚠️ **重要**：不要直接提交大型二进制文件（音频、视频、图片）到 Git。

而是在 `artifacts/raw_pointers/` 中创建指针文件：

**示例：`artifacts/raw_pointers/audio/voice_master.pointer.json`**

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
  "contains_sensitive_data": true
}
```

## 第四步：验证你的档案

提交前，验证你的档案：

```bash
# 返回仓库根目录
cd /path/to/DLRS

# 运行验证
python tools/validate_repo.py
```

如果验证通过，你会看到：
```
✓ All validations passed
✓ humans/asia/cn/dlrs_12345678_zhang-san/manifest.json is valid
```

如果有错误，工具会显示需要修复的内容。

## 第五步：构建索引（针对公开档案）

如果你的档案是公开的（`visibility: public_indexed` 或 `public_unlisted`）：

```bash
python tools/build_registry.py
```

这会更新 `registry/humans.index.jsonl` 文件。

## 第六步：提交和推送

```bash
# 添加你的新档案
git add humans/asia/cn/dlrs_12345678_zhang-san/

# 使用描述性的提交信息
git commit -m "Add: 张三的数字生命档案"

# 推送到远程
git push origin main
```

## 第七步：提交 Pull Request（针对公共仓库）

如果你是向公共 DLRS Hub 贡献：

1. **Fork 仓库** 在 GitHub 上
2. **创建新分支**：`git checkout -b add-zhangsan-record`
3. **推送分支**：`git push origin add-zhangsan-record`
4. **在 GitHub 上打开 Pull Request**
5. **选择模板**：`.github/PULL_REQUEST_TEMPLATE/human-record.md`
6. **填写 PR 描述**：
   - 档案 ID
   - 可见性级别
   - 同意验证方法
   - 任何特殊考虑
7. **等待维护者审核**

## 常见问题和解决方案

### 问题：验证失败，提示"缺少必填字段"

**解决方案**：检查 `manifest.json` 中的所有必填字段是否已填写。与 `humans/asia/cn/dlrs_94f1c9b8_lin-example/` 中的示例对比。

### 问题："档案 ID 已存在"

**解决方案**：选择不同的档案 ID。每个 ID 在整个仓库中必须唯一。

### 问题："检测到敏感文件"

**解决方案**：你可能不小心提交了大型二进制文件。使用 `.pointer.json` 文件代替。运行：

```bash
python tools/check_sensitive_files.py
```

### 问题：找不到 Python 依赖

**解决方案**：确保已安装依赖：

```bash
pip install -r tools/requirements.txt
```

## 下一步

现在你已经创建了第一个档案，你可以：

1. **添加更多制品** - 添加音频、视频、图片等的指针
2. **配置运行时** - 在 `runtime/` 中设置运行时配置
3. **添加派生数据** - 在 `derived/` 中包含嵌入向量、记忆原子等
4. **设置继承** - 在 `profile/inheritance_policy.json` 中配置继承策略
5. **审查政策** - 阅读 `policies/` 以了解合规要求

## 其他资源

- [架构概览](architecture.md)
- [常见问题](FAQ.md)
- [贡献指南](../CONTRIBUTING.md)
- [上传指南](upload-guide.md)
- [示例档案](../examples/)

## 获取帮助

如果遇到问题：

- 查看 [FAQ](FAQ.md)
- 在 GitHub 上开 issue
- 联系：https://github.com/Digital-Life-Repository-Standard/DLRS/discussions

---

**恭喜！** 🎉 你已成功创建了第一个 DLRS Hub 档案。
