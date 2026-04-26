# DLRS 实现与终极标准的差距分析

> 版本：v0.6 release（2026-04 刷新）
> 上一版基线：v0.5 release，整体完成度 83%
> 本次基线：post-v0.6 epic #52（PRs #64–#75），整体完成度 **~88%**

## 📊 执行摘要

本文档对比当前 DLRS 仓库实现与 `DLRS_ULTIMATE.md` 中定义的完整标准，识别已实现、部分实现、尚未实现三档。读者可以把本文当成"运营进度仪表盘"。

| 维度 | v0.2.0 基线 | v0.3 | v0.4 | v0.5 | v0.6 (本次) | ULTIMATE 目标 |
|---|---|---|---|---|---|---|
| 仓库与目录 | 90% | 95% | 95% | 95% | **95%** | 100%（pointer-first 完成） |
| 数据采集规范 | 40% | 80% | 85% | 85% | **85%** | 100% |
| 数据分层与存储 | 50% | 65% | 70% | 75% | **80%**（`derived/memory_atoms/` + `derived/knowledge_graph/` 落地） | 100% |
| 同意与权益 | 70% | 85% | 88% | 88% | **88%** | 100% |
| 公开层与注册表 | 30% | 70% | 80% | 80% | **80%** | 100% |
| 审计与事件 | 40% | 50% | 70% | 70% | **80%**（descriptor→audit 桥接上链 + `derived_asset_emitted` 入 enum） | 100%（含 Ledger / 联邦审计） |
| 权限模型 (RBAC/ReBAC/ABAC) | 0% | 0% | 0% | 0% | **0%** | 100%（v0.7+ 实施） |
| 构建管线 (ASR/KG/微调) | 0% | 0% | 0% | 45% | **65%**（6 条离线管线 + descriptor + audit bridge + hosted-API gate + CI；GraphRAG 语义搜索 / 微调 留 v0.7+） | 100% |
| 运行层 (REST/WS/3D) | 0% | 0% | 0% | 0% | **0%** | 100%（v0.7+ 实施） |
| AI 标识 / 水印 / C2PA | 5% | 10% | 35% | 40% | **45%**（descriptor 机械化离线证明 + hosted-API gate 机械化"何时允许 online"） | 100%（v1.0 实施） |
| 跨境 / 法域引擎 | 30% | 50% | 55% | 55% | **55%** | 100% |
| 工具与自动化 | 40% | 75% | 88% | 94% | **96%**（+ memory_atoms / KG / audit_bridge / hosted_api_policy / memory_graph_demo 测试） | 100% |

**总体成熟度**：⭐⭐⭐⭐ **88%**（v0.5 → v0.6 增长 5 pp，主要拉动来自构建管线 45% → 65% 与审计 70% → 80%）

- ✅ **已完成**：v0.2–v0.5 的所有内容，加上 v0.6 的两条新管线（memory_atoms / knowledge_graph）+ memory atom / entity-graph node / entity-graph edge / hosted-api-policy 四份新 schema + descriptor→audit/events.jsonl 机械桥接 + hosted-API opt-in 策略门 + `examples/memory-graph-demo` 端到端示例 + `docs/PIPELINE_GUIDE.md` v0.6 刷新。
- 🟡 **部分完成**：hosted-API 策略门只落框架，实际 hosted SDK 接入留 v0.7；GraphRAG 真语义搜索 / 微调管线 / talking head 未开工；Web 审核台原型下沉到 v0.7+。
- ❌ **未实现**：运行层（REST/WS/3D）、RBAC/ReBAC/ABAC、C2PA 实际签发、联邦化注册表同步。

---

## 1. 仓库层（Repository Layer）

### ✅ 已实现（95%）

| 功能 | v0.4 状态 | 说明 |
|------|------|------|
| 基础目录结构 | ✅ | `humans/`, `templates/`, `examples/`, `schemas/`, `audit/` |
| manifest.json 规范 | ✅ | v0.3.0 schema，含 `public_disclosure`、`audit.events_log_ref` |
| 指针文件系统 | ✅ | `.pointer.json` 显式禁止凭据/下载 URL |
| 公开/私有可见性 | ✅ | 含 `public_indexed` / `public_unlisted` |
| 删除策略 | ✅ | 含 `withdrawal_effect` enum、`legal_hold` |
| 继承策略 | ✅ | `inheritance_policy.default_action_on_death` enum |
| 审计字段 | ✅ | `change_log_hash` + `events_log_ref` |
| `.gitattributes` (LFS 防御) | ✅ **v0.4** | `docs/LFS_GUIDE.md` |
| GitHub Actions CI | ✅ | `.github/workflows/validate.yml`（双 job：validate + docs） |
| 敏感文件检测 | ✅ | `tools/check_sensitive_files.py` 在 CI 主链路 |

### 🟡 部分实现（80%）

| 功能 | 状态 | 缺失部分 |
|------|------|----------|
| Schema 收紧 | 🟡 | `if/then` 已引入但只覆盖 visibility→public_disclosure 一条；其余跨字段约束（如 voice_clone→biometric_consent）尚未硬约束 |
| 大文件 LFS | 🟡 | `.gitattributes` 已加，但未在 CI 显式拒绝非 LFS 大文件（`check_sensitive_files.py` 间接拦截） |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| DVC / lakeFS 集成 | 低 | v0.6+（构建管线启动后） |

---

## 2. 数据采集规范（Data Collection Standards）

### ✅ 已实现（85%）

| 功能 | 状态 | 说明 |
|------|------|------|
| 最低采集规范 | ✅ | `docs/COLLECTION_STANDARD.md`（音频 44.1k/16-bit/≥60s、视频 720p24/≥30s、图像 ≥512px、文本 ≥10k） |
| 高保真指南 | ✅ | `docs/HIGH_FIDELITY_GUIDE.md`（low/mid/high 三档） |
| 指针元数据格式 | ✅ | `pointer.schema.json` |
| 敏感度分级 | ✅ | `S0_PUBLIC` 到 `S4_RESTRICTED` |
| 媒体元数据自动校验 | ✅ | `tools/validate_media.py`（ffprobe） |
| 对象存储指针文档 | ✅ | `docs/OBJECT_STORAGE_POINTERS.md` |

### 🟡 部分实现

| 功能 | 状态 | 缺失部分 |
|------|------|----------|
| 文本语料规范 | 🟡 | 在 `COLLECTION_STANDARD.md` 中只有最低字数；语义/时序约束未细化 |
| 3D Avatar 规范 | 🟡 | VRM/glTF/FBX 格式列出，但未给出材质 / 蒙皮 / blendshape 规范表 |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| Audio2Face / 全身动作 | 低 | v3.0 |
| Blendshape 情绪标签 | 中 | v0.7 |

---

## 3. 数据分层与存储（Data Layering）

### 🟡 部分实现（80%）

| 功能 | 状态 | 说明 |
|------|------|------|
| 五层目录约定 | ✅ | Raw（pointers）/Derived/Runtime/Index/Audit 全部建目录 |
| Raw 层 | ✅ | pointer-first，仓库零原始素材 |
| Derived 层 | ✅ **v0.6** | `derived/<pipeline>/` 现覆盖 6 条管线：asr/text/vectorization/moderation/memory_atoms/knowledge_graph 均产生合同 descriptor |
| Runtime 层 | 🟡 | 目录 OK，**模型权重 pointer 占位**（v0.7 运行时上线） |
| Index 层 | 🟡 **v0.5** | `pipelines/vectorization/` 可选推送本地 Qdrant；v0.6 加了 `derived/knowledge_graph/{nodes,edges}.jsonl`；真语义 GraphRAG 留给 v0.7+ |
| Audit 层 | ✅ **v0.6** | `events.jsonl` + emitter + 哈希链（v0.4）；v0.6 增 `derived_asset_emitted` 事件上链 + descriptor.audit_event_ref 反填 |

### 🟡 部分实现 / 待 v0.7+

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| ASR 转写管线 | 高 | ✅ v0.5（`pipelines/asr/`） |
| 文本清洗管线 | 高 | ✅ v0.5（`pipelines/text/`） |
| 向量化管线 | 高 | ✅ v0.5（`pipelines/vectorization/` + 可选 Qdrant） |
| 内容审核管线 | 高 | ✅ v0.5（`pipelines/moderation/`） |
| Memory atoms 抽取 | 中 | ✅ v0.6（`pipelines/memory_atoms/`） |
| 知识图谱（共现边） | 中 | ✅ v0.6（`pipelines/knowledge_graph/`） |
| descriptor 哈希链上链到 audit/events.jsonl | 中 | ✅ v0.6（`pipelines/_audit_bridge.py`） |
| GraphRAG 真语义检索 / Neo4j | 中 | v0.7+ |
| 语音克隆训练 (TTS) | 中 | v0.7 |

---

## 4. 同意与权益（Consent & Rights）

### ✅ 已实现（88%）

| 功能 | 状态 | 说明 |
|------|------|------|
| consent_statement.md 模板 | ✅ | `humans/_TEMPLATE/consent/` |
| 同意撤回端点 | ✅ | `consent.withdrawal_endpoint`（必填） |
| 单独生物特征同意 | ✅ | `consent.separate_biometric_consent` |
| 权利依据 | ✅ | `rights.rights_basis[]` |
| 跨境基础 | ✅ | `cross_border_transfer_basis` enum |
| 撤回流程模板 | ✅ | `.github/ISSUE_TEMPLATE/consent-withdrawal.yml` |
| 下架流程模板 | ✅ | `.github/ISSUE_TEMPLATE/takedown-request.yml` |
| 冒名争议模板 | ✅ | `.github/ISSUE_TEMPLATE/impersonation-dispute.yml` |
| 合规自检 checklist | ✅ **v0.4** | `docs/COMPLIANCE_CHECKLIST.md` |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| 自动化撤回执行 | 高 | v0.5（runtime 出现后） |
| 同意到期自动 take-down | 中 | v0.5 |

---

## 5. 公开层与注册表（Public Registry）

### ✅ 已实现（80%）

| 功能 | 状态 | 说明 |
|------|------|------|
| `humans.index.jsonl` 生成 | ✅ | `tools/build_registry.py` |
| `humans.index.csv` 生成 | ✅ | 同上 |
| **`registry/index.html` 静态页** | ✅ **v0.4** | 内联 CSS、零依赖 |
| 入选规则 | ✅ | `public_indexed/unlisted` + `approved_public` + (verified-consent ∨ public-data-only)，is_minor 排除 |
| 入选规则单元测试 | ✅ | `tools/test_registry.py` 14 个用例（v0.3 起 12 → v0.4 起 14） |
| Badge 系统 | ✅ | verified-consent / public-data-only / restricted-runtime / cross-border-blocked / memorial-review-required |
| `examples/minor-protected` | ✅ **v0.4** | 验证 is_minor 排除 |
| `examples/estate-conflict-frozen` | ✅ **v0.4** | 验证 legal_hold + blocked 排除 |

### 🟡 部分实现

| 功能 | 状态 | 缺失部分 |
|------|------|----------|
| Web 审核台 | 🟡 | v0.4 仅静态 HTML；可交互审核台**已下沉至 v0.6+** |
| 联邦同步协议 | ❌ | 未启动；`docs/REGISTRY_FEDERATION.md` 待写 |

---

## 6. 审计与事件（Audit & Events）

### ✅ 已实现（80%）

| 功能 | 状态 | 说明 |
|------|------|------|
| `audit/events.jsonl` 约定 | ✅ **v0.4** | append-only，按行 JSON |
| Audit event schema | ✅ | `schemas/audit-event.schema.json`：8 个 v0.4 核心 + 1 个 v0.6 (`derived_asset_emitted`) + custom |
| Emitter 工具 | ✅ **v0.4** | `tools/emit_audit_event.py`（含哈希链 + 重复 event_id 拒写） |
| 8 个 v0.4 核心事件类型 | ✅ | record_created / consent_verified / build_started / public_listing_requested / consent_withdrawn / take_down / inheritance_trigger / export_requested |
| **`derived_asset_emitted` 事件类型** | ✅ **v0.6** | 每条管线在写完 descriptor 后追加；descriptor.audit_event_ref 反填为 `audit/events.jsonl#L<n>` |
| **descriptor → audit 机械桥接** | ✅ **v0.6** | `pipelines/_audit_bridge.py`；复用 v0.4 emitter 哈希链；无 manifest 静默 no-op；`--no-audit` 跳过 |
| Provenance 占位 | ✅ | `audit/provenance.json` |
| Takedown 日志 | ✅ | `audit/takedown_log.jsonl` |

### 🟡 部分实现

| 功能 | 状态 | 缺失部分 |
|------|------|----------|
| 哈希链 | 🟡 | 文件内已链 + descriptor 反填；跨文件 / 跨记录 ledger 未实施 |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| 不可篡改 Ledger / 区块链锚定 | 低 | v1.0+ |
| Audit query API | 中 | v0.7（与 REST API 同步） |

---

## 7. 权限模型（RBAC + ReBAC + ABAC）

### ❌ 未实现（0%）

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| RBAC（角色） | 高 | v0.7 |
| ReBAC（OpenFGA） | 高 | v0.8 |
| ABAC（OPA / Cedar） | 高 | v0.8 |
| 法域策略阻断 | 高 | v0.7（与 RBAC 同步） |
| 敏感度访问门控 | 高 | v0.7 |
| Legal Hold 强制 | 中 | v0.7 |

**注**：v0.4 把权限/审计的 schema 与文档坐标系打稳，但实施需要 runtime 出现后才有意义。**v0.4 不再宣称"v0.7-v0.8 单独 RBAC"**——已修订 ROADMAP，把 RBAC 合并进 REST API 出生即引入的设计。

---

## 8. 构建层（Build Pipeline）

### 🟡 部分实现（65%，v0.6 拉高）

| 功能 | 状态 | 计划版本 | 说明 |
|------|------|------|------|
| Whisper / faster-whisper 转写 | ✅ **v0.5** | — | `pipelines/asr/`：`dummy`（确定性、零依赖）+ `faster-whisper`（懒加载）双后端 |
| 文本解析与清洗 | ✅ **v0.5** | — | `pipelines/text/`：NFKC 正规化 + 保守正则脱敏，redactions 旁注不回写原文 |
| Embedding 生成 | ✅ **v0.5** | — | `pipelines/vectorization/`：`hash`（64-D 确定性）+ `sentence-transformers`（懒加载） |
| 向量库推送 | ✅ **v0.5** | — | `--qdrant-url` 可选本地 Qdrant；payload 中 `backend` / `model_id` 分键 |
| 内容审核 | ✅ **v0.5** | — | `pipelines/moderation/`：确定性 regex/wordlist + `pass / flag / block`；flag 不回写匹配文本 |
| **记忆原子抽取** | ✅ **v0.6** | — | `pipelines/memory_atoms/`：`paragraph` 默认零依赖 + `spacy` 可选懒加载；`<stem>.atoms.jsonl` |
| **知识图谱（共现边）** | ✅ **v0.6** | — | `pipelines/knowledge_graph/`：regex 后端；字面空格，标签不含 `\n`（PR #71 回归） |
| Derived-asset descriptor | ✅ **v0.5** | — | `schemas/derived-asset.schema.json` + `pipelines/_descriptor.py`；online_api_used 强制 false |
| Hosted-API 离线守卫 | ✅ **v0.5** | — | `tools/validate_pipelines.py` 静态拒收 hosted-API import（v0.6 不放松） |
| **descriptor → audit 桥接** | ✅ **v0.6** | — | `pipelines/_audit_bridge.py` 追加 `derived_asset_emitted` 事件 + 反填 `audit_event_ref` |
| **hosted-API opt-in 策略门** | ✅ **v0.6** | — | `schemas/hosted-api-policy.schema.json` + `pipelines/_hosted_api.py`；默认拒绝 + per-record opt_in + 时间窗 |
| FunASR / 多说话人分离 | 🟡 | v0.7 | v0.5/v0.6 只携 faster-whisper；说话人分离 留给 v0.7 |
| GraphRAG 真语义检索 | ❌ | v0.7 | v0.6 是共现边图谱，不是嵌入式检索 |
| Hosted-API SDK 实际接入 | ❌ | v0.7 | v0.6 仅落策略门框架；逐管线在 gate 后 importlib 引入 |
| 语音克隆训练 (TTS) | ❌ | v0.7 | 与 runtime 同步引入 |
| Talking Head 训练 | ❌ | v0.8 | — |
| 3D Avatar 构建 | ❌ | v2.0 | — |
| C2PA 凭证生成 | ❌ | v1.0 | 与水印实施同步 |

---

## 9. 运行层（Runtime）

### ❌ 未实现（0%）

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| 文本对话 / LLM 集成 | 高 | v0.6 |
| TTS 推理 | 高 | v0.7 |
| 实时 ASR | 中 | v0.7 |
| Talking Head 推理 | 中 | v0.8 |
| 3D Avatar runtime | 中 | v2.0+ |
| REST API | 高 | v0.7 |
| WebSocket / Realtime | 中 | v0.8 |
| 长期记忆 / RAG | 高 | v0.6 |

---

## 10. AI 标识、水印、C2PA

### ✅ 已实现（45%）

| 功能 | 状态 | 说明 |
|------|------|------|
| `public_disclosure` 字段 | ✅ **v0.4** | 公有可见性下硬约束 (`if/then`) |
| `ai_disclosure` enum | ✅ **v0.4** | visible_label_required / visible_label_and_watermark / c2pa_required |
| 多语言标签 | ✅ **v0.4** | `label_locales[]` 含 zh-CN / en |
| `watermark_methods[]` 声明 | ✅ **v0.4** | enum 占位（实施在 v1.0） |
| Descriptor `online_api_used=false` 机械化证明 | ✅ **v0.5** | 每条派生资产 descriptor 必须声明未调用托管 API，`tools/validate_pipelines.py` 静态拒收 hosted-API import |
| **hosted-API opt-in 策略门** | ✅ **v0.6** | `schemas/hosted-api-policy.schema.json` + `pipelines/_hosted_api.py` 机械化“何时允许 online”；默认拒绝 + per-record opt_in + provider/pipeline 白名单 + 时间窗 |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| 视频/图像不可见水印 | 高 | v1.0 |
| AudioSeal 音频水印 | 中 | v1.0+ |
| C2PA 实际签发 | 高 | v1.0 |
| 文本零宽水印 | 低 | v1.0+ |
| 第三方分类器接入 | 中 | v1.0 |

---

## 11. 跨境与法域

### 🟡 部分实现（55%）

| 功能 | 状态 | 说明 |
|------|------|------|
| 主区域字段 | ✅ | `security.primary_region` |
| 复制区域字段 | ✅ | `security.replication_regions[]` |
| 跨境基础 enum | ✅ | `cross_border_transfer_basis` |
| 跨境状态 | ✅ | `cross_border_transfer_status`（v0.3 增加 `blocked`） |
| **合规自检文档** | ✅ **v0.4** | `docs/COMPLIANCE_CHECKLIST.md`（PIPL / GDPR / EU AI Act / 中国深度合成办法） |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| 法域策略引擎（运行时阻断） | 高 | v0.7（与 RBAC 同步） |
| 自动化跨境合规检查 | 中 | v0.7 |

---

## 12. 工具与自动化

### ✅ 已实现（96%）

| 工具 | v0.2 | v0.3 | v0.4 | v0.5 | v0.6 | 描述 |
|---|---|---|---|---|---|---|
| `validate_repo.py` | ✅ | ✅ | ✅ | ✅ | ✅ | 全仓 manifest 校验 |
| `validate_manifest.py` | ✅ | ✅ | ✅ | ✅ | ✅ | 单 manifest CLI |
| `new_human_record.py` | ✅ | ✅ | ✅ | ✅ | ✅ | 档案脚手架 |
| `i18n_helper.py` | ✅ | ✅ | ✅ | ✅ | ✅ | i18n 辅助 |
| `check_sensitive_files.py` | ✅ | ✅ | ✅ | ✅ | ✅ | 防御性敏感文件检测 |
| `build_registry.py` | ✅ | ✅ | ✅ | ✅ | ✅ | jsonl + csv + **html (v0.4)** |
| `lint_schemas.py` | – | ✅ | ✅ | ✅ | ✅ | Draft 2020-12 校验 |
| `validate_examples.py` | – | ✅ | ✅ | ✅ | ✅ | 示例校验 |
| `validate_media.py` | – | ✅ | ✅ | ✅ | ✅ | ffprobe pointer 校验 |
| `test_registry.py` | – | ✅ (12) | ✅ (14) | ✅ (14) | ✅ (14) | registry 入选规则用例 |
| `upload_to_storage.py` | – | ✅ | ✅ | ✅ | ✅ | 对象存储上传骨架 |
| `estimate_costs.py` | – | ✅ | ✅ | ✅ | ✅ | 容量/费用估算 |
| `batch_validate.py` | – | – | ✅ **v0.4** | ✅ (11/11) | ✅ (16/16) | 一次性聚合 + JSON 报告 |
| `emit_audit_event.py` | – | – | ✅ **v0.4** | ✅ | ✅ | append-only 审计写入器 |
| `run_pipeline.py` | – | – | – | ✅ **v0.5** | ✅ (6) | 统一管线 CLI 入口 (asr/text/vec/mod/memory_atoms/KG) |
| `validate_pipelines.py` | – | – | – | ✅ **v0.5** | ✅ | hosted-API import 黑名单 + `derived/<spec.name>/` 输出前缀守卫（v0.6 不放松） |
| `test_pipelines.py` | – | – | – | ✅ **v0.5** | ✅ (9/9) | 统一测试驱动（6 per-pipeline + 3 横切） |
| `test_asr_demo.py` | – | – | – | ✅ **v0.5** | ✅ | `examples/asr-demo` 端到端测试 |
| `test_derived_asset_schema.py` | – | – | – | ✅ **v0.5** | ✅ | `schemas/derived-asset.schema.json` 健全性测试 |
| **`test_memory_atom_schema.py`** | – | – | – | – | ✅ **v0.6** | `schemas/memory-atom.schema.json` 17 个 sanity 用例 |
| **`test_entity_graph_schema.py`** | – | – | – | – | ✅ **v0.6** | KG node/edge schema 22 个 sanity 用例 |
| **`test_memory_atoms_pipeline.py`** | – | – | – | – | ✅ **v0.6** | memory_atoms 管线测试（含 leak-guard） |
| **`test_knowledge_graph_pipeline.py`** | – | – | – | – | ✅ **v0.6** | knowledge_graph 管线测试 |
| **`test_descriptor_audit_bridge.py`** | – | – | – | – | ✅ **v0.6** | descriptor→audit 桥接测试（含哈希链跨管线、`--no-audit`、无 manifest 静默 no-op） |
| **`test_hosted_api_policy.py`** | – | – | – | – | ✅ **v0.6** | hosted-API 策略门测试（schema golden + 6 反例 + 默认拒绝 + 时间窗） |
| **`test_memory_graph_demo.py`** | – | – | – | – | ✅ **v0.6** | `examples/memory-graph-demo` 端到端测试 |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| LFS 大文件 CI 拦截器 | 中 | v0.5 |
| Web 审核台 | 中 | v0.6+ |
| 联邦化 sync agent | 低 | v0.7+ |

---

## 13. 与 ULTIMATE 的主要差距（截至 v0.6）

| 差距 | 现状 | 影响 | 处置 |
|---|---|---|---|
| 构建管线进一步拉高（~65%） | v0.6 交付 6 条离线管线 + descriptor + audit bridge + hosted-API gate + CI；GraphRAG 真语义搜索 / TTS / talking head / 3D / C2PA 未开工 | 已能证明“仓库 → 派生资产 + 双向审计”闭环，运行时能力仍缺 | v0.7 运行时 + 托管 SDK 接入；v0.8+ 多模态生成 |
| hosted-API 调用未接入实际 SDK | v0.6 只落策略门框架，不写实际 SDK 调用方 | 接入者需手动在 gate 后面补 importlib + 运行时调用 | v0.7，逐管线加 |
| RBAC / ReBAC / ABAC 缺失 | schema 已有 sensitivity / cross-border / hosted-api-policy 字段，但运行时没人执行 | 公网部署不可控 | v0.7 与 REST API 同步 |
| Web 审核台缺失 | 仅静态 HTML | 大规模运营审核效率低 | v0.7+，与 runtime 一同推出 |
| C2PA / 水印实施缺失 | v0.5 descriptor `online_api_used=false` + v0.6 hosted-API gate 机械化证明离线 / 何时 online；实际水印 / C2PA 凭证未签发 | 输出可信度依赖外部检测器 | v1.0 |
| 国际化 / 法域引擎缺失 | 文档化，未引擎化 | 合规风险靠 review 兜底 | v0.7（与 RBAC 同步） |
| descriptor 哈希上链 → 已交付 | ✅ v0.6 audit bridge 把 6 条管线的 descriptor 全部追加为 `derived_asset_emitted` 事件上哈希链；`audit_event_ref` 双向反填 | 追溯性增强；远端审核可以从事件 → descriptor 召回 | 其余联邦化上链留 v1.0 |
| 联邦化注册表缺失 | 仅单仓单 jsonl | 难以多机构协同 | v1.0+ |

---

## 14. 路线图与本文档的关系

- 本文档 = **现状对照表**，反映**已落地**与**ULTIMATE 目标**之间的距离。
- `ROADMAP.md` = **时间表**，给出每个版本期望交付什么。
- `DLRS_ULTIMATE.md` = **目标态**，是本文档对照的基准。

读者如果只想看"今天能用什么"，看本文档第 1–6、12 节即可；如果想看"什么时候能用"，看 `ROADMAP.md`；如果想看"最终长什么样"，看 `DLRS_ULTIMATE.md`。

---

**文档版本**：4.0（v0.6 release）
**上次更新**：2026-04-26（v0.6 epic #52，PRs #64–#75）
**下次更新建议**：v0.6（GraphRAG / online-enhanced / descriptor 哈希上链上线后）
