# DLRS Hub 实施状态总结

> 详细差距分析见 `docs/GAP_ANALYSIS.md`。本文是"高速摘要"。

## 📊 快速概览

**当前版本**: v0.6.0
**总体完成度**: ~88%
**参考标准**: DLRS_ULTIMATE.md
**最近发布**: v0.6 epic #52（PRs #64–#75）
**进行中**: `.life Archive + Runtime Standard` 愿景升级 — epic [#79](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/79)、子 issue #80–#87。本次升级把 ULTIMATE 从"Git-shaped 仓库结构标准"重新定位为"`.life` 文件格式 + runtime 协议双标准"；本 epic 只交付 specs + schema + example builder（**不**含 runtime 实现，运行时实现推迟到 v0.8+）。

### v0.5 → v0.6 主要增量

- **新增两条离线管线**：
  - `pipelines/memory_atoms/` — `paragraph`（默认、零依赖）+ `spacy`（懒加载、可选）双后端；输出 `<stem>.atoms.jsonl`，每行一条 atom；绝对字符偏移可往返反查 cleaned text；`schemas/memory-atom.schema.json`（13 字段、11 必填、`additionalProperties: false`）。
  - `pipelines/knowledge_graph/` — `regex` 后端，候选实体使用字面空格（不是 `\s+`，避免标签里出现 `\n`，PR #71 的回归保证）；输出 `<stem>.{nodes,edges}.jsonl` + 单一 graph descriptor；`schemas/entity-graph-node.schema.json` + `schemas/entity-graph-edge.schema.json`。
- **descriptor → audit/events.jsonl 桥接**（v0.4 哈希链上链）：6 条管线在写完 descriptor 后追加一条 `derived_asset_emitted` 事件并把 `audit/events.jsonl#L<n>` 反填到 descriptor.audit_event_ref；复用 v0.4 emitter 的哈希链（不引入新链语义），`schemas/audit-event.schema.json::event_type.enum` 增 1 个值，其余 8 条 v0.4 lifecycle 事件不变；每条管线 CLI 新增 `--no-audit` 用于 fixture / dry-run。
- **hosted-API opt-in 策略门**：`schemas/hosted-api-policy.schema.json` + `pipelines/_hosted_api.py`。默认离线优先不变；唯一打开 hosted 调用的方式是记录级 `policy/hosted_api.json` 显式声明 `opt_in: true` + provider/pipeline 白名单 + 同意凭证 + `[issued_at, expires_at)` 时间窗。`assert_allowed` 任一条件不满足即抛 `HostedApiNotAllowed`。本 PR 只落框架，不写 hosted SDK 调用方；静态 import ban 不放松，hosted SDK 必须 `importlib` 懒加载在 gate 之内。
- **统一测试驱动**：`tools/test_pipelines.py` 现在派发 6 条 per-pipeline + 3 条 v0.6 横切（audit_bridge / hosted_api_policy / memory_graph_demo）= 9/9。CI 矩阵 `pipelines` 一步替代之前 4 个分散步骤；`batch_validate` 16/16（保留个别条目以保留报错粒度）。
- **端到端示例**：`examples/memory-graph-demo/` —— `bash run_demo.sh` 一键产出 8 个派生工件 + 3 行哈希链审计；零 hosted-API 调用、零网络。
- **文档**：`docs/PIPELINE_GUIDE.md` 落地两条新管线 + audit bridge §3 + hosted-API gate §4 + 作者向导补 audit-bridge / 策略门两步；GAP / STATUS / ROADMAP / CHANGELOG / README 全面刷新到 v0.6。
- **治理硬规则**（v0.5 起永久生效）：每个子 issue 一个 PR；PR body 必须以 `Closes #N` 单独成行显式列出。v0.6 epic #52 严格遵守 11/11。

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

## ✅ 已完成的核心功能（v0.6）

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

### 3. 工具和脚本（96%）
- ✅ `validate_repo.py` / `validate_manifest.py` / `validate_examples.py`
- ✅ `validate_media.py`（ffprobe pointer 元数据校验）
- ✅ `lint_schemas.py`（Draft 2020-12 schema 校验）
- ✅ `build_registry.py`（jsonl + csv + **html**）
- ✅ `test_registry.py`（14 个 registry 入选规则用例）
- ✅ `new_human_record.py`、`i18n_helper.py`、`check_sensitive_files.py`
- ✅ `upload_to_storage.py`、`estimate_costs.py`
- ✅ `batch_validate.py` —— 聚合所有 validator + JSON 报告（v0.6 现 16/16 step）
- ✅ `emit_audit_event.py` —— append-only 审计事件写入器（含哈希链）
- ✅ `run_pipeline.py` —— 统一管线入口（asr / text / vectorization / moderation / memory_atoms / knowledge_graph 子命令）
- ✅ `validate_pipelines.py` —— 静态守卫（hosted-API import 黑名单 + `derived/<spec.name>/` 输出前缀强制；v0.6 不放松）
- ✅ `test_pipelines.py` —— 统一测试驱动（v0.6 派发 6 条 per-pipeline + 3 条横切 = 9/9）
- ✅ `test_asr_demo.py` —— v0.5 端到端示例测试
- ✅ `test_derived_asset_schema.py` —— v0.5 派生资产 descriptor schema 健全性测试
- ✅ **`test_memory_atom_schema.py`** —— v0.6 memory atom schema 17 个 sanity 用例
- ✅ **`test_entity_graph_schema.py`** —— v0.6 KG node + edge schema 22 个 sanity 用例
- ✅ **`test_memory_atoms_pipeline.py`** —— v0.6 memory_atoms 管线测试（含 leak-guard）
- ✅ **`test_knowledge_graph_pipeline.py`** —— v0.6 knowledge_graph 管线测试
- ✅ **`test_descriptor_audit_bridge.py`** —— v0.6 descriptor → audit/events.jsonl 桥接测试（含哈希链跨管线、`--no-audit` 跳过、无 manifest 静默 no-op）
- ✅ **`test_hosted_api_policy.py`** —— v0.6 hosted-API 策略门测试（schema golden + 6 反例 + 默认拒绝 + 时间窗 + 畸形 JSON）
- ✅ **`test_memory_graph_demo.py`** —— v0.6 端到端 demo 测试

### 4. 构建管线（65%，v0.6 拉动从 45%）
- ✅ `pipelines/__init__.py` —— `PipelineSpec` 注册表 + 分发（6 条管线）
- ✅ `pipelines/_descriptor.py` —— 共享 `DescriptorBuilder`，对接 `schemas/derived-asset.schema.json`
- ✅ **`pipelines/_audit_bridge.py`** —— v0.6 descriptor → `audit/events.jsonl` 桥接（每个 descriptor 写入后追加一条 `derived_asset_emitted` 事件 + 反填 `audit_event_ref`）
- ✅ **`pipelines/_hosted_api.py`** —— v0.6 hosted-API opt-in 策略门（`assert_allowed` 任一条件不满足即抛 `HostedApiNotAllowed`；只落框架不写 SDK 调用方）
- ✅ `pipelines/asr/` —— `dummy`（确定性、零依赖）+ `faster-whisper`（懒加载）双后端
- ✅ `pipelines/text/` —— NFKC 正规化 + 保守正则脱敏（含凭据 URL、邮箱、CN 身份证、CN 手机、IPv4、信用卡号、通用电话号）；替换使用类别 token（`<EMAIL>` / `<PHONE_CN>` / `<ID_CN>` / `<IPV4>` / `<CARD>` / `<PHONE>` / `<URL_WITH_CREDENTIALS>`）
- ✅ `pipelines/vectorization/` —— 段落感知切分 + 绝对字符偏移 + `hash` / `sentence-transformers` + 可选本地 Qdrant
- ✅ `pipelines/moderation/` —— 确定性 regex/wordlist 策略 + 严重度聚合（pass / flag / block）+ `--policy-file`
- ✅ **`pipelines/memory_atoms/`** —— `paragraph`（默认、零依赖）+ `spacy`（懒加载、可选）；`<stem>.atoms.jsonl` + 字符偏移往返
- ✅ **`pipelines/knowledge_graph/`** —— `regex` 后端；候选用字面空格避免 `\n` 进 label（PR #71 回归）；nodes + edges + graph descriptor
- ✅ **`examples/memory-graph-demo/`** —— v0.6 端到端示例（`bash run_demo.sh` 一键产出 8 个派生工件 + 3 行哈希链审计）
- ✅ `examples/asr-demo/` —— v0.5 端到端示例（4 条管线、9 个派生工件、4 份 descriptor）
- 🟡 GraphRAG / 真正语义搜索 / 微调管线 —— 留给 v0.7
- 🟡 hosted-API SDK 实际接入 —— 留给 v0.7（v0.6 已落策略门 + lazy import 范式）

---

## 🟡 / ❌ 详细差距

为避免文档双向漂移，所有部分完成 / 未实现的清单都迁移到 `docs/GAP_ANALYSIS.md` 单一来源。摘要：

- **构建管线**（ASR / 文本 / 向量 / 审核 / memory atoms / KG）—— **65%**：v0.6 已落地六条离线管线 + descriptor + audit bridge + hosted-API gate + CI；GraphRAG 真语义搜索 / TTS / 微调 / talking head 留给 v0.7+。
- **审计 & 事件**—— **80%**：v0.6 把 descriptor 上链到 `audit/events.jsonl` 哈希链；剩余差距在 Ledger / 联邦审计同步（v1.0）。
- **AI 标识 & 水印**—— **45%**：descriptor `online_api_used` 静态强制 false + hosted-API gate 把 "何时允许 online" 机械化；视频/图像/音频水印、C2PA 实际签发推到 v1.0。
- **运行层**（LLM 对话、TTS、实时 ASR、talking head、3D、REST/WS）—— 0%，v0.7 起逐步开工。
- **权限模型**（RBAC / ReBAC / ABAC、法域策略引擎、Legal Hold 强制）—— 0%，v0.7 与 REST API 同步引入。
- **联邦化注册表**—— 未启动，v1.0+ 候选。

详细对照表：[`docs/GAP_ANALYSIS.md`](GAP_ANALYSIS.md)。

---

## 💡 关键建议（v0.6 视角）

1. 保持"仓库优先 + pointer-first"。即使构建管线已落地 6 条 + audit bridge + hosted-API gate，标准文档与 schema 仍是 DLRS 的根基；管线只读 manifest / 写 `derived/`，不反向修改根 schema。
2. **v0.6 memory + graph + audit + opt-in policy 已交付**：六条管线 + descriptor schema + audit bridge + hosted-API gate 全部 merged；CI 在没有任何 hosted API key 的情况下全绿；`tools/test_pipelines.py` 9/9，`batch_validate` 16/16。
3. **v0.7 = runtime + RBAC**：在 v0.6 基础上叠 REST/WS API + LLM 推理 + RBAC/ReBAC/ABAC，把 schema 字段（sensitivity / cross-border / legal_hold / hosted-api-policy）真正接入运行时；避免"v0.7 单纯 REST、v0.8 才接入授权"的两次 breaking change。
4. **hosted-API**：v0.6 已经把策略门做硬（per-record opt-in + provider/pipeline 白名单 + 时间窗 + 静态 import ban 不放松 + 必须 importlib 懒加载在 gate 之内），v0.7 起逐条管线接入实际 SDK 时严格走这条路径，不要绕开。
5. **AI 标识**：v0.4 把声明做硬，v0.5 把 descriptor `online_api_used=false` 做成机械化离线证明，v0.6 把 audit bridge 把每条 derived 上链 + hosted gate 把"何时允许 online"机械化；v1.0 把水印 / C2PA 实施做硬。中间版本不要回退已收紧的 schema 或静态 import ban。
6. 所有破坏性 schema 调整必须先发 issue + 走 v0.X.0 minor，不在 patch 版本里改 enum；`audit-event.schema.json::event_type.enum` 在 v0.6 增了 1 条值（`derived_asset_emitted`）即遵守此规则。
7. **治理硬规则**（v0.5 起永久生效，v0.6 epic #52 11/11 遵守）：每个子 issue 一个 PR；PR body 必须以 `Closes #N` 单独成行显式列出；任何引入托管 API import 的 commit 在 CI 阶段即被 `tools/validate_pipelines.py` 拒绝。

---

**文档版本**: 4.0（v0.6 release）
**最后更新**: 2026-04-26
**参考**: DLRS_ULTIMATE.md, docs/GAP_ANALYSIS.md, ROADMAP.md
