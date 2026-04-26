# DLRS 实现与终极标准的差距分析

> 版本：v0.5 release（2026-04 刷新）
> 上一版基线：v0.4 release，整体完成度 78%
> 本次基线：post-v0.5 epic #28（PRs #39–#48），整体完成度 **~83%**

## 📊 执行摘要

本文档对比当前 DLRS 仓库实现与 `DLRS_ULTIMATE.md` 中定义的完整标准，识别已实现、部分实现、尚未实现三档。读者可以把本文当成"运营进度仪表盘"。

| 维度 | v0.2.0 基线 | v0.3 | v0.4 | v0.5 (本次) | ULTIMATE 目标 |
|---|---|---|---|---|---|
| 仓库与目录 | 90% | 95% | 95% | **95%** | 100%（pointer-first 完成） |
| 数据采集规范 | 40% | 80% | 85% | **85%** | 100% |
| 数据分层与存储 | 50% | 65% | 70% | **75%**（`derived/<pipeline>/` 落地 + descriptor schema） | 100% |
| 同意与权益 | 70% | 85% | 88% | **88%** | 100% |
| 公开层与注册表 | 30% | 70% | 80% | **80%** | 100% |
| 审计与事件 | 40% | 50% | 70% | **70%** | 100%（含哈希链/Ledger） |
| 权限模型 (RBAC/ReBAC/ABAC) | 0% | 0% | 0% | **0%** | 100%（v0.7+ 实施） |
| 构建管线 (ASR/KG/微调) | 0% | 0% | 0% | **45%**（4 条离线管线 + descriptor + CI；GraphRAG/微调留 v0.6+） | 100% |
| 运行层 (REST/WS/3D) | 0% | 0% | 0% | **0%** | 100%（v0.7+ 实施） |
| AI 标识 / 水印 / C2PA | 5% | 10% | 35% | **40%**（descriptor 强制 `online_api_used=false`，机械化离线证明） | 100%（v1.0 实施） |
| 跨境 / 法域引擎 | 30% | 50% | 55% | **55%** | 100% |
| 工具与自动化 | 40% | 75% | 88% | **94%**（+ `run_pipeline` / `validate_pipelines` / `test_pipelines` / `test_asr_demo`） | 100% |

**总体成熟度**：⭐⭐⭐⭐ **83%**（v0.4 → v0.5 增长 5 pp，主要拉动来自原本 0% 的"构建管线"维度首次落地到 45%）

- ✅ **已完成**：v0.2–v0.4 的所有内容，加上 v0.5 的四条离线管线（asr/text/vectorization/moderation）+ derived-asset descriptor schema + `tools/run_pipeline.py` 单入口 + `tools/validate_pipelines.py` 静态守卫（机械化执行的离线优先不变量）+ `examples/asr-demo` 端到端示例 + `docs/PIPELINE_GUIDE.md`。
- 🟡 **部分完成**：构建管线只覆盖 ASR / 文本 / 向量 / 审核，GraphRAG / memory atoms / 微调留给 v0.6；descriptor 写入 `derived/`，append-only 哈希链上链尚未对接 emitter。
- ❌ **未实现**：运行层（REST/WS/3D）、RBAC/ReBAC/ABAC、Web 审核台原型（已下沉到 v0.6+）、C2PA 实际签发、联邦化注册表同步。

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

### 🟡 部分实现（75%）

| 功能 | 状态 | 说明 |
|------|------|------|
| 五层目录约定 | ✅ | Raw（pointers）/Derived/Runtime/Index/Audit 全部建目录 |
| Raw 层 | ✅ | pointer-first，仓库零原始素材 |
| Derived 层 | ✅ **v0.5** | `derived/<pipeline>/` 实际打通：asr/text/vectorization/moderation 均产生合同 descriptor |
| Runtime 层 | 🟡 | 目录 OK，**模型权重 pointer 占位**（v0.7 运行时上线） |
| Index 层 | 🟡 **v0.5** | `pipelines/vectorization/` 可可选推送本地 Qdrant；GraphRAG / Neo4j 留给 v0.6 |
| Audit 层 | ✅ **v0.4** | `events.jsonl` + emitter + 哈希链 |

### 🟡 部分实现 / 待 v0.6

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| ASR 转写管线 | 高 | ✅ v0.5（`pipelines/asr/`） |
| 文本清洗管线 | 高 | ✅ v0.5（`pipelines/text/`） |
| 向量化管线 | 高 | ✅ v0.5（`pipelines/vectorization/` + 可选 Qdrant） |
| 内容审核管线 | 高 | ✅ v0.5（`pipelines/moderation/`） |
| GraphRAG / Neo4j 图谱 | 中 | v0.6 |
| Memory atoms | 中 | v0.6（"在线增强"） |
| descriptor 哈希链上链到 audit/events.jsonl | 中 | v0.6 |

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

### ✅ 已实现（70%）

| 功能 | 状态 | 说明 |
|------|------|------|
| `audit/events.jsonl` 约定 | ✅ **v0.4** | append-only，按行 JSON |
| Audit event schema | ✅ | `schemas/audit-event.schema.json`：8 个核心 enum + custom |
| Emitter 工具 | ✅ **v0.4** | `tools/emit_audit_event.py`（含哈希链 + 重复 event_id 拒写） |
| 8 个核心事件类型 | ✅ | record_created / consent_verified / build_started / public_listing_requested / consent_withdrawn / take_down / inheritance_trigger / export_requested |
| Provenance 占位 | ✅ | `audit/provenance.json` |
| Takedown 日志 | ✅ | `audit/takedown_log.jsonl` |

### 🟡 部分实现

| 功能 | 状态 | 缺失部分 |
|------|------|----------|
| 哈希链 | 🟡 | 文件内已链；跨文件 / 跨记录 ledger 未实施 |

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

### 🟡 部分实现（45%，v0.5 首次落地）

| 功能 | 状态 | 计划版本 | 说明 |
|------|------|------|------|
| Whisper / faster-whisper 转写 | ✅ **v0.5** | — | `pipelines/asr/`：`dummy`（确定性、零依赖）+ `faster-whisper`（懒加载）双后端 |
| 文本解析与清洗 | ✅ **v0.5** | — | `pipelines/text/`：NFKC 正规化 + 保守正则脱敏，redactions 旁注不回写原文 |
| Embedding 生成 | ✅ **v0.5** | — | `pipelines/vectorization/`：`hash`（64-D 确定性）+ `sentence-transformers`（懒加载） |
| 向量库推送 | ✅ **v0.5** | — | `--qdrant-url` 可选本地 Qdrant；payload 中 `backend` / `model_id` 分键 |
| 内容审核 | ✅ **v0.5** | — | `pipelines/moderation/`：确定性 regex/wordlist + `pass / flag / block`；flag 不回写匹配文本 |
| Derived-asset descriptor | ✅ **v0.5** | — | `schemas/derived-asset.schema.json` + `pipelines/_descriptor.py`；online_api_used 强制 false |
| Hosted-API 离线守卫 | ✅ **v0.5** | — | `tools/validate_pipelines.py` 静态拒收 hosted-API import |
| FunASR / 多说话人分离 | 🟡 | v0.6 | v0.5 只携 faster-whisper；FunASR / 说话人分离 留给 v0.6 |
| 记忆原子抽取 | ❌ | v0.6（online-enhanced） | — |
| GraphRAG 知识图谱 | ❌ | v0.6 | — |
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

### ✅ 已实现（40%）

| 功能 | 状态 | 说明 |
|------|------|------|
| `public_disclosure` 字段 | ✅ **v0.4** | 公有可见性下硬约束 (`if/then`) |
| `ai_disclosure` enum | ✅ **v0.4** | visible_label_required / visible_label_and_watermark / c2pa_required |
| 多语言标签 | ✅ **v0.4** | `label_locales[]` 含 zh-CN / en |
| `watermark_methods[]` 声明 | ✅ **v0.4** | enum 占位（实施在 v1.0） |
| Descriptor `online_api_used=false` 机械化证明 | ✅ **v0.5** | 每条派生资产 descriptor 必须声明未调用托管 API，`tools/validate_pipelines.py` 静态拒收 hosted-API import |

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

### ✅ 已实现（94%）

| 工具 | v0.2 | v0.3 | v0.4 | v0.5 | 描述 |
|---|---|---|---|---|---|
| `validate_repo.py` | ✅ | ✅ | ✅ | ✅ | 全仓 manifest 校验 |
| `validate_manifest.py` | ✅ | ✅ | ✅ | ✅ | 单 manifest CLI |
| `new_human_record.py` | ✅ | ✅ | ✅ | ✅ | 档案脚手架 |
| `i18n_helper.py` | ✅ | ✅ | ✅ | ✅ | i18n 辅助 |
| `check_sensitive_files.py` | ✅ | ✅ | ✅ | ✅ | 防御性敏感文件检测 |
| `build_registry.py` | ✅ | ✅ | ✅ | ✅ | jsonl + csv + **html (v0.4)** |
| `lint_schemas.py` | – | ✅ | ✅ | ✅ | Draft 2020-12 校验 |
| `validate_examples.py` | – | ✅ | ✅ | ✅ | 示例校验 |
| `validate_media.py` | – | ✅ | ✅ | ✅ | ffprobe pointer 校验 |
| `test_registry.py` | – | ✅ (12) | ✅ (14) | ✅ (14) | registry 入选规则用例 |
| `upload_to_storage.py` | – | ✅ | ✅ | ✅ | 对象存储上传骨架 |
| `estimate_costs.py` | – | ✅ | ✅ | ✅ | 容量/费用估算 |
| `batch_validate.py` | – | – | ✅ **v0.4** | ✅ (11/11) | 一次性聚合 + JSON 报告 |
| `emit_audit_event.py` | – | – | ✅ **v0.4** | ✅ | append-only 审计写入器 |
| **`run_pipeline.py`** | – | – | – | ✅ **v0.5** | 统一管线 CLI 入口 |
| **`validate_pipelines.py`** | – | – | – | ✅ **v0.5** | hosted-API import 黑名单 + `derived/<spec.name>/` 输出前缀守卫 |
| **`test_pipelines.py`** | – | – | – | ✅ **v0.5** | 子进程驱动运行 4 条管线 + descriptor 测试 |
| **`test_asr_demo.py`** | – | – | – | ✅ **v0.5** | `examples/asr-demo` 端到端测试 |
| **`test_derived_asset_schema.py`** | – | – | – | ✅ **v0.5** | `schemas/derived-asset.schema.json` 健全性测试 |

### ❌ 未实现

| 功能 | 优先级 | 计划版本 |
|------|--------|------|
| LFS 大文件 CI 拦截器 | 中 | v0.5 |
| Web 审核台 | 中 | v0.6+ |
| 联邦化 sync agent | 低 | v0.7+ |

---

## 13. 与 ULTIMATE 的主要差距（截至 v0.5）

| 差距 | 现状 | 影响 | 处置 |
|---|---|---|---|
| 构建管线部分落地（~45%） | v0.5 交付 4 条离线管线 + descriptor + CI；GraphRAG / TTS / talking head / 3D / C2PA 未开工 | 已能证明“仓库 → 派生资产”闭环，但在线增强 / 运行时能力仍缺 | v0.6 叠 GraphRAG / online-enhanced；v0.7 运行时 |
| RBAC / ReBAC / ABAC 缺失 | schema 已有 sensitivity / cross-border 字段，但运行时没人执行 | 公网部署不可控 | v0.7 与 REST API 同步 |
| Web 审核台缺失 | 仅静态 HTML | 大规模运营审核效率低 | v0.6+，与 runtime 一同推出 |
| C2PA / 水印实施缺失 | v0.5 用 descriptor `online_api_used=false` 机械化证明离线；实际水印 / C2PA 凭证未签发 | 输出可信度依赖外部检测器 | v1.0 |
| 国际化 / 法域引擎缺失 | 文档化，未引擎化 | 合规风险靠 review 兜底 | v0.7（与 RBAC 同步） |
| descriptor 哈希未上链 | v0.5 已生成 descriptor + sha256，但未写入 audit/events.jsonl 哈希链 | 可追溯性变弱，外部审核需手动拼接 | v0.6（与 online-enhanced 同期） |
| 联邦化注册表缺失 | 仅单仓单 jsonl | 难以多机构协同 | v1.0+ |

---

## 14. 路线图与本文档的关系

- 本文档 = **现状对照表**，反映**已落地**与**ULTIMATE 目标**之间的距离。
- `ROADMAP.md` = **时间表**，给出每个版本期望交付什么。
- `DLRS_ULTIMATE.md` = **目标态**，是本文档对照的基准。

读者如果只想看"今天能用什么"，看本文档第 1–6、12 节即可；如果想看"什么时候能用"，看 `ROADMAP.md`；如果想看"最终长什么样"，看 `DLRS_ULTIMATE.md`。

---

**文档版本**：3.0（v0.5 release）
**上次更新**：2026-04-26（v0.5 epic #28，PRs #39–#48）
**下次更新建议**：v0.6（GraphRAG / online-enhanced / descriptor 哈希上链上线后）
