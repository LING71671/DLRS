# DLRS Hub 实施状态总结

> 详细差距分析见 `docs/GAP_ANALYSIS.md`。本文是"高速摘要"。

## 📊 快速概览

**当前版本**: v0.8-asset-architecture（epic [#106](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/106) 收尾）
**总体完成度**: ~82%（v0.7 的 ~80% 基础上 +Asset Architecture 四补丁 + Tier 系统 + 5-stage assembly；v0.9 runtime 参考实现仍是最大缺口）
**参考标准**: DLRS_ULTIMATE.md（已升级为"`.life` 文件格式 + runtime 协议双标准"）
**最近发布**: v0.8-asset-architecture epic #106（PRs #107、#108、#109、#110、#111、#112、#113、#114、#115、#116 — 6 个 sub-issue 全部交付 + 4 个 post-merge follow-up）
**仍在跑**: 无（epic #106 全部 6 个 sub-issue 已合；下一程跨入 v0.9 Reference Runtime Implementation，详见 ROADMAP.md）。

### v0.8 主要增量（epic #106）

- **`docs/LIFE_ASSET_ARCHITECTURE.md`** — 4 补丁（Genesis / Lifecycle / Binding / Assembly）+ Tier 系统的架构总览文档；锁定 D1–D6 决策、Schema D Cosmic Evolution 命名表（Quark → Singularity）、拒绝的备选方案附录、与 v0.7 spec 的衔接说明。
- **`docs/LIFE_GENESIS_SPEC.md` + `schemas/genesis.schema.json`** — 每个派生资产的 `genesis/<asset_id>.genesis.json` 字段规范（method / source_inputs / compute / consent_scope_checked / audit_event_ref），base_model 作为虚资产、reproducibility_level 三档、consent_scope enum。
- **`docs/LIFE_LIFECYCLE_SPEC.md` + `schemas/lifecycle.schema.json`** — 包级 supersedes / lifecycle_state / memorial_metadata，资产级 lifecycle + mutation log JSONL，cascade_index.json，semver+hash 双标识，分叉允许 / 合并禁止，mark tainted 撤回级联，7 天 memorial 异议期。
- **`docs/LIFE_BINDING_SPEC.md` + `schemas/binding.schema.json`** — `binding/runtime_binding.json` 字段（capabilities / orchestration / hard_constraints / surface / hosted_api_preference），capability 词表 hybrid（核心 enum + `x-` 扩展前缀），engine.strict、hard_constraints fail-close。
- **`docs/LIFE_TIER_SPEC.md` + `schemas/tier.schema.json` + `docs/appendix/TIER_NAMING_SCHEMA_D.md`** — 6 维度（identity / asset_completeness / consent / detail / audit_chain / jurisdiction）加权派生 score 0–100 → 12 档（I–XII），机器字段冻结 + name/glyph 进可演化附录；取代 v0.7 `verification_level`（向后兼容保留）。
- **`docs/LIFE_RUNTIME_STANDARD.md` Part B** — 5 阶段 assembly（Verify / Resolve / Assemble / Run / Guard）+ Provider Registry + `LifeCapabilityProvider` 接口 + 分级沙箱（built-in / user-installed OS 进程级；`.life`-bundled v0.8 禁止）+ hosted-API AND-gate（binding 允许 AND user opt-in）+ OS 包管理器 bootstrap + 4 条新审计事件（capability_bound / assembly_aborted / withdrawal_poll / lifecycle_transition_observed）。
- **`schemas/life-package.schema.json` + `tools/build_life_package.py` v0.2** — tier 块集成到 top-level descriptor（optional，v0.7 back-compat），builder 自动从 contents + CLI 覆盖派生 6 维 → 计分 → 带 name/glyph 写回 descriptor；hand-rolled tier 被 `computed_by` 模式（必须 `@` 分隔）直接 schema 层拒绝。

### ULTIMATE 重新定位的影响（v0.7-vision-shift）

epic #79 把 DLRS 的目标态从"Git-shaped 仓库结构标准"升级为：

> **DLRS 定义 `.life` 文件格式 + runtime 协议**。`.life` 是经本人或合法授权方许可生成的数字生命档案包；兼容 runtime 加载 `.life` 后在聊天系统、虚拟世界、3D 场景或其他数字环境中生成可交互、可撤回、可审计的 **AI digital life instance**（不是"真人复活"）。

本次 epic **只**交付 specs + schema + example builder，**不**含 runtime 实现：

- `docs/LIFE_FILE_STANDARD.md` — `.life` 档案格式权威规范（life-format v0.1.0）
- `docs/LIFE_RUNTIME_STANDARD.md` — `.life` 兼容 runtime 协议（life-runtime v0.1）
- `schemas/life-package.schema.json` — 每个 `.life` 内 `life-package.json` 的契约（Draft 2020-12，54/54 sanity 用例通过）
- `examples/minimal-life-package/` + `tools/build_life_package.py` — life-format v0.1.0 参考 builder（pointer-mode、确定性 zip、自动 schema 校验、跨两次构建字节稳定）
- `README.md` / `README.en.md` 第一屏重新定位
- `ROADMAP.md` 新增两条独立 semver 主线（`.life Archive Standard` 与 `.life Runtime Standard`，独立于本仓库的 v0.x.y）
- `audit-event.schema.json::event_type.enum` 新增 `package_emitted`（向后兼容追加）

**总体完成度回调说明**：v0.6 报告的 88% 是相对"仓库结构 + 离线管线 + 派生资产"为目标态计算的。新 ULTIMATE 把 ".life runtime 实例化" 列为关键交付，本 epic 不实现 runtime（推迟到 v0.8+）。因此把目标线推远的同时已交付维度并不变化，整体百分比按新分母回调到 ~80%。详细分维度见 `docs/GAP_ANALYSIS.md` 第 0 节（v0.7 重新定位维度）和 §1–§14。

### v0.6 → v0.7-vision-shift 主要增量

- **`.life` Archive Standard 落地**（specs + schema + example builder）：
  - `docs/LIFE_FILE_STANDARD.md`：定义 `.life` zip 内的强制目录（manifest/consent/policy/audit/derived）+ 可选目录（pointers/encrypted）+ 双形态（pointer / encrypted）+ 强制元字段（mode、record_id、issued_by、consent_evidence_ref、verification_level、withdrawal_endpoint、runtime_compatibility、ai_disclosure、forbidden_uses、audit_event_ref、contents、expires_at）+ 伦理边界（不是"真人复活"，必须可标识 / 可撤回 / 可审计）。
  - `schemas/life-package.schema.json`：54 个 sanity 用例覆盖 happy paths + 反例（pointer/encrypted bi-conditional、memorial→executor bi-conditional、sha256 大小写不敏感、forbidden_uses 必须包含 fraud/political/explicit、`expires_at > created_at`、contents 路径不允许 `..` 或绝对路径）。
  - `examples/minimal-life-package/` + `tools/build_life_package.py`：6 步实现 §5 authoring workflow（stage / append `package_emitted` audit event / 计算 sha256 inventory / 写 life-package.json / 校验 / 确定性 zip）；e2e 测试两次确定性构建字节相同。
- **`.life` Runtime Standard 落地**（specs only，runtime 实现推迟 v0.8+）：
  - `docs/LIFE_RUNTIME_STANDARD.md`：定义 8 步加载序列（验证 schema → 时间窗 → 完整性 → 审计链 → consent 解析 → 撤回端点轮询 → mount → 标识/撤回/审计就位）+ runtime 强制义务（disclosure label、forbidden_uses[] 拒绝、≥ 24h withdrawal 轮询、expires_at 拒绝继续、跨 `.life` 不混合记忆）+ 终止触发器 + 禁止行为 + 一致性条款 + 伦理边界。
- **README 第一屏重新定位**：DLRS = `.life` 双标准（档案格式 + runtime 协议）；"What is DLRS?" 拆为 archive format / runtime protocol / supporting infrastructure 三段；"What is NOT" 与 "What IS" 显式 `.life` 框定（不是真人复活、必须可撤回 / 可审计 / 始终标识为 AI 实例）。
- **ROADMAP 双轨**：新增 "Track A — `.life` Archive Standard"（life-format v0.1.0 / v0.2.0 / v0.3.0）和 "Track B — `.life` Runtime Standard"（life-runtime v0.1 / v0.2 / v0.3）两条独立 semver 主线，独立于本仓库 v0.x.y；明确 ".life Archive" 是文件格式契约，".life Runtime" 是协议契约，两者互相独立但联合定义 DLRS 终极交付。
- **审计事件 enum 追加**：`schemas/audit-event.schema.json::event_type.enum` 新增 `package_emitted`（life-format v0.1.0 builder 在源记录 `audit/events.jsonl` 上链使用），仿 v0.6 `derived_asset_emitted` 模式向后兼容追加。
- **治理硬规则**（v0.5 起永久生效）：每 sub-issue 一个 PR；PR body `Closes #N` 单独成行；epic #79 8/8 严格遵守，post-merge bug 走单独 issue→PR（#90→#91、#96→#97），不 amend 已合 PR。

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

## 💡 关键建议（v0.7-vision-shift 视角）

1. **`.life` 是新的核心交付**。仓库结构 / 管线 / 派生资产是"如何造"，`.life` 档案 + runtime 协议是"对外的交付物"。v0.7+ 任何新管线 / 新字段都先问"会不会进 `.life` 包？runtime 加载时怎么处理？"，而不是只问"放哪个目录"。
2. **specs 与 implementation 分轨**。`life-format` 与 `life-runtime` 各自独立 semver（见 ROADMAP.md），独立于本仓库的 v0.x.y。修 spec → 走 life-format / life-runtime semver；修 builder / 校验工具 → 走仓库 v0.x.y。两条版本号不能耦合。
3. **runtime 推迟到 v0.8+ 是有意识的选择**。先把 specs / schema / example builder 钉死，再写 runtime；避免 runtime 实现反向污染 spec（典型反模式："既然 runtime 已经这么做了，就不修 spec 了"）。
4. **encrypted-mode `.life` 推迟到 life-format v0.2 + KMS 接入**。v0.1 builder 主动拒绝 `--mode encrypted` 不是缺陷，是有意识的 staging 策略；schema 里两个 mode 都已就位，等 KMS 落地直接接入即可。
5. **签名机制推迟到 life-format v0.2**。v0.1 `signature_ref` 是不透明字符串，v0.2 引入实际签名算法（候选：JOSE / ed25519）。在 v0.1 阶段任何"我自己实现一个签名格式"的尝试都应被劝退；签发链的语义影响 runtime 信任模型，不能急。
6. **保持"离线优先 + pointer-first"不变**。v0.5/v0.6 的硬规则（descriptor `online_api_used=false`、`tools/validate_pipelines.py` 静态 import ban、hosted-API gate）在 v0.7-vision-shift 全部继承不放松；`.life` pointer mode 默认是隐私优先的形态。
7. **AI 标识**：v0.6 已机械化"何时允许 online"，v0.7-vision-shift 进一步把 `ai_disclosure` 列为 `.life` 强制元字段（`visible_label_required` 是最低线）；runtime 实现时"输出 token 不带可见标识 → block" 必须做硬。中间版本不要回退已收紧的 schema 或静态 import ban。
8. **schema enum 追加规则**：`audit-event.schema.json::event_type.enum` 在 v0.7-vision-shift 又追加了 1 条 `package_emitted`（v0.6 已加 `derived_asset_emitted`），仍遵守"破坏性 schema 调整走 minor、不在 patch 版本里改 enum"。
9. **治理硬规则**（v0.5 起永久生效，v0.6 epic #52 11/11 遵守，v0.7-vision-shift epic #79 8/8 遵守）：每个子 issue 一个 PR；PR body 必须以 `Closes #N` 单独成行显式列出；post-merge bug 走单独 issue→PR（#77→#78、#90→#91、#96→#97），永远不 amend / 不 force-push 已合 PR。

---

**文档版本**: 6.0（v0.8-asset-architecture release，epic #106 收尾）
**最后更新**: 2026-04-26
**参考**: DLRS_ULTIMATE.md（已升级为 `.life` 双标准），docs/GAP_ANALYSIS.md, docs/LIFE_FILE_STANDARD.md, docs/LIFE_RUNTIME_STANDARD.md, docs/LIFE_ASSET_ARCHITECTURE.md, docs/LIFE_TIER_SPEC.md, ROADMAP.md
