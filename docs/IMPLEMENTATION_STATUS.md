# DLRS Hub 实施状态总结

> 详细差距分析见 `docs/GAP_ANALYSIS.md`。本文是"高速摘要"。

## 📊 快速概览

**当前版本**: v0.5.0
**总体完成度**: ~83%
**参考标准**: DLRS_ULTIMATE.md
**最近发布**: v0.5 epic #28（PRs #39–#48）

### v0.4 → v0.5 主要增量

- **管线契约**：`pipelines/__init__.py` 注册 `PipelineSpec`，`tools/run_pipeline.py` 提供单一 CLI 入口；`tools/validate_pipelines.py` 静态守卫强制 `derived/<spec.name>/` 输出前缀 + 拒绝任何 hosted-API import（机械化执行的离线优先不变量）。
- **派生资产 schema**：`schemas/derived-asset.schema.json` + `pipelines/_descriptor.py` 让每条 pipeline 输出都附带 provenance descriptor（who/what/where/hashes），`model.online_api_used` 始终为 `false`。
- **四条离线管线**：
  - `pipelines/asr/` — `dummy`（确定性）+ `faster-whisper`（懒加载）双后端；多语言 + 时间戳；`--device cpu|cuda`。
  - `pipelines/text/` — NFKC 正规化 + 保守正则脱敏（含凭据 URL、邮箱、CN 身份证、CN 手机、IPv4、信用卡号、通用电话号）；替换使用类别 token（`<EMAIL>` / `<PHONE_CN>` / `<ID_CN>` / `<IPV4>` / `<CARD>` / `<PHONE>` / `<URL_WITH_CREDENTIALS>`）；`redactions.json` 旁注仅记 `kind + start/end + replacement`，永远不回写原文。
  - `pipelines/vectorization/` — 段落感知切分 + 绝对字符偏移；`hash`（确定性 64-D）+ `sentence-transformers` 双后端；可选本地 Qdrant 推送（`backend` / `model_id` 分键）。
  - `pipelines/moderation/` — 确定性 regex/wordlist 策略 + 严重度聚合（`pass | flag | block`）；`--policy-file` JSON/YAML 自定义；flag 永远不回写匹配文本。
- **CI 集成**：`.github/workflows/validate.yml` 新增 `pipelines` 矩阵 job（Python 3.11 / 3.12）；`tools/test_pipelines.py` 子进程驱动 + `tools/batch_validate.py` 11 个 step 全绿。
- **端到端示例**：`examples/asr-demo/` 自包含、确定性 placeholder WAV、`bash run_demo.sh` 一键产出 9 个派生工件 + 4 份 descriptor，全程不需要联网。
- **文档**：`docs/PIPELINE_GUIDE.md` 落地 contract / descriptor / 各管线 CLI / 作者向导 / v0.5 不在范围的事；GAP/STATUS/ROADMAP/CHANGELOG 全面刷新到 v0.5。
- **治理硬规则**（v0.5 起永久生效）：每个子 issue 一个 PR，PR body 必须以 `Closes #N` 单独成行显式列出，避免 v0.3/v0.4 的逗号串列被 GitHub 忽略导致 stale issue 大批留存。

---

## ✅ 已完成的核心功能（v0.5）

### 1. 仓库基础设施（95%）
- ✅ 完整的目录结构（`humans/`, `templates/`, `examples/`, `schemas/`）
- ✅ `manifest.json` 规范（包含所有核心字段）
- ✅ 指针文件系统（`.pointer.json`）
- ✅ 同意证据管理（`consent/` 目录）
- ✅ 继承策略（`inheritance_policy.json`）
- ✅ 删除策略（`deletion_policy`）
- ✅ 区域化和跨境字段
- ✅ 基础审计字段

### 2. 文档体系（92%）
- ✅ `docs/COLLECTION_STANDARD.md`、`docs/HIGH_FIDELITY_GUIDE.md`、`docs/OBJECT_STORAGE_POINTERS.md`、`docs/LFS_GUIDE.md`、`docs/COMPLIANCE_CHECKLIST.md`
- ✅ 详细的 README（保姆级教程）
- ✅ 完整的 Getting Started 指南
- ✅ 30+ 问答的 FAQ
- ✅ 贡献指南
- ✅ 中英文双语支持（i18n）
- ✅ 4 个示例档案

### 3. 工具和脚本（94%）
- ✅ `validate_repo.py` / `validate_manifest.py` / `validate_examples.py`
- ✅ `validate_media.py`（ffprobe pointer 元数据校验）
- ✅ `lint_schemas.py`（Draft 2020-12 schema 校验）
- ✅ `build_registry.py`（jsonl + csv + **html**）
- ✅ `test_registry.py`（14 个 registry 入选规则用例）
- ✅ `new_human_record.py`、`i18n_helper.py`、`check_sensitive_files.py`
- ✅ `upload_to_storage.py`、`estimate_costs.py`
- ✅ `batch_validate.py` —— 聚合所有 validator + JSON 报告（v0.5 现 11/11 step）
- ✅ `emit_audit_event.py` —— append-only 审计事件写入器（含哈希链）
- ✅ **`run_pipeline.py`** —— v0.5 单一管线入口（asr / text / vectorization / moderation 子命令）
- ✅ **`validate_pipelines.py`** —— v0.5 静态守卫（hosted-API import 黑名单 + `derived/<spec.name>/` 输出前缀强制）
- ✅ **`test_pipelines.py`** —— v0.5 子进程驱动，运行 4 条管线 + descriptor 测试
- ✅ **`test_asr_demo.py`** —— v0.5 端到端示例测试
- ✅ **`test_derived_asset_schema.py`** —— v0.5 派生资产 descriptor schema 健全性测试

### 4. 构建管线（45%，v0.5 新增维度）
- ✅ `pipelines/__init__.py` —— `PipelineSpec` 注册表 + 分发
- ✅ `pipelines/_descriptor.py` —— 共享 `DescriptorBuilder`，对接 `schemas/derived-asset.schema.json`
- ✅ `pipelines/asr/` —— `dummy`（确定性、零依赖）+ `faster-whisper`（懒加载）双后端
- ✅ `pipelines/text/` —— NFKC 正规化 + 保守正则脱敏（含凭据 URL、邮箱、CN 身份证、CN 手机、IPv4、信用卡号、通用电话号）；替换使用类别 token（`<EMAIL>` / `<PHONE_CN>` / `<ID_CN>` / `<IPV4>` / `<CARD>` / `<PHONE>` / `<URL_WITH_CREDENTIALS>`）
- ✅ `pipelines/vectorization/` —— 段落感知切分 + 绝对字符偏移 + `hash` / `sentence-transformers` + 可选本地 Qdrant
- ✅ `pipelines/moderation/` —— 确定性 regex/wordlist 策略 + 严重度聚合（pass / flag / block）+ `--policy-file`
- ✅ `examples/asr-demo/` —— 自包含端到端示例（`bash run_demo.sh` 一键产出 9 个派生工件 + 4 份 descriptor）
- 🟡 GraphRAG / memory atoms / 微调管线 —— 留给 v0.6
- 🟡 descriptor append-only 哈希链上链（与 `emit_audit_event.py` 对接）—— 留给 v0.6

---

## 🟡 / ❌ 详细差距

为避免文档双向漂移，所有部分完成 / 未实现的清单都迁移到 `docs/GAP_ANALYSIS.md` 单一来源。摘要：

- **构建管线**（ASR / 文本 / 向量 / 审核）—— **45%**：v0.5 已落地四条离线管线 + descriptor + CI；GraphRAG / 微调 / memory atoms 留给 v0.6。
- **运行层**（LLM 对话、TTS、实时 ASR、talking head、3D、REST/WS）—— 0%，v0.7 起逐步开工。
- **权限模型**（RBAC / ReBAC / ABAC、法域策略引擎、Legal Hold 强制）—— 0%，v0.7 与 REST API 同步引入。
- **AI 标识 & 水印实施**（视频/图像/音频水印、C2PA 实际签发）—— schema 层已完备，实施推到 v1.0。
- **联邦化注册表**—— 未启动，v1.0+ 候选。

详细对照表：[`docs/GAP_ANALYSIS.md`](GAP_ANALYSIS.md)。

---

## 💡 关键建议（v0.5 视角）

1. 保持"仓库优先 + pointer-first"。即使构建管线已落地，标准文档与 schema 仍是 DLRS 的根基；管线只读 manifest / 写 `derived/`，不反向修改根 schema。
2. **v0.5 offline-first 已交付**：四条管线（asr / text / vectorization / moderation）+ descriptor schema 全部 merged，CI 在没有任何 hosted API key 的情况下全绿。
3. **v0.6 = online-enhanced**：在 v0.5 基础上叠 GraphRAG / memory atoms / 可选托管 API（同 backend 接口、关闭即默认离线）；以及把 descriptor 的 hash 上链到 `audit/events.jsonl` 哈希链。
4. **v0.7 与 REST API 同步引入 RBAC / ReBAC / ABAC**——把 schema 字段（sensitivity, cross-border, legal_hold）真正接入运行时，避免"v0.7 单纯 RBAC、v0.8 才接入"的两次 breaking change。
5. **AI 标识**：v0.4 把声明做硬，v0.5 把 descriptor 的 `online_api_used=false` 做成机械化离线证明，v1.0 把水印 / C2PA 实施做硬；中间版本不要回退已收紧的 schema。
6. 所有破坏性 schema 调整必须先发 issue + 走 v0.X.0 minor，不在 patch 版本里改 enum。
7. **治理硬规则**（v0.5 起永久生效）：每个子 issue 一个 PR；PR body 必须以 `Closes #N` 单独成行显式列出；任何引入托管 API import 的 commit 在 CI 阶段即被 `tools/validate_pipelines.py` 拒绝。

---

**文档版本**: 3.0（v0.5 release）
**最后更新**: 2026-04-26
**参考**: DLRS_ULTIMATE.md, docs/GAP_ANALYSIS.md, ROADMAP.md
