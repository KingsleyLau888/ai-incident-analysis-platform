# AI Incident Copilot：项目基线、审查结果与后续工作指南

> 每次开始工作或运行演示前先读本文件。它是当前维护计划的主入口，不要每次重新设计项目。
>
> 审查日期：2026-09-08。参照提交：`1e25c6e`，**包含审查时工作区未提交修改**，不是该提交的纯净快照。
> 标准：L3，可交接、可验证的长期项目；按本地原型评估，不假定已经上线。
> 本次交付是审查与文档约定，**下列业务问题尚未修复**。

## 1. 当前接续状态：下次从这里开始

| 项目 | 当前记录 |
|---|---|
| 本轮完成 | Runbook 检索重优化（用户批准计划）：chunk 类型标注计分制修复误标、查询构建带入证据词、过滤策略与融合参数全消融；27 例 Top-1 55.56%→88.89%、Recall 77.16%→84.57%；22 例消融 tfidf 单查询 Top-1 100%；4 后端对比 hybrid 92.59%。随后按"小步消化"节奏修复 F07（Judge 静默失效：27/27 出分）、F01（分析结果原子性：persistence 进度移至提交后 + 3 项故障注入测试）、F15（反馈存在性 404 + 正反馈正确性过滤 + 竞态收敛）与 F13（Dashboard 竞态：过期响应丢弃 + run ID 缓存 + 404 空态与统计卡口径，92 passed）与 F14（SSE 查询限额 + 流式接口真进度不阻塞事件循环 + simulated 如实标注，98 passed）、F02（任务幂等与启动恢复：原子领取、成功重入不重跑、开机清场、接口防连点，105 passed）、F03（事故去重依赖初步类型、事故任务原子提交、并发单建锁+唯一索引、手动分析建任务、服务重名稳定返回，115 passed）、F04（时间账本：入账统一 UTC（实测旧代码 +08:00 偏 8 小时）、计数窗口补上界、received_at 送达时间、source 出身代替标题、手动分析窗口封顶，129 passed）、F16（可选接入钥匙门锁 + 请求大小/写入频率限额 + 凭据不泄漏，140 passed）。**P0 全部收工（A 路线 + 共享部署安全边界）** |
| 当前阶段 | 主链路功能已存在，正确性与可信度收敛阶段（P0 完成） |
| 建议下一项 | F10/F12 真实模型评测剩余指标、SQLite FK pragma（F15 遗留，孤儿扫描后开启）等 P1 事项；待用户消化后选 |
| 随后处理 | F05/F06（Agent 取证前置条件与证据来源，中高工作量）；F17（配置治理）/F18（日志接入缓冲）按需 |
| 随后处理 | F16：真实数据/共享部署前安全边界 |
| 评测前置项 | F07 已完成（2026-09-09）：Judge 序列化修复、requested/attempted/succeeded/failed/skipped 显式统计与脱敏错误；可继续讨论真实模型质量评测（F10/F12 剩余指标） |
| 暂缓 | 新 Agent 框架、更多检索后端、多 Agent 协作、自动修复、大规模前端重写 |
| 运行基线 | Mock + TF-IDF + pipeline，关闭 CrossEncoder，单进程、本地隔离数据 |
| 未验证 | 真实模型 API、多进程重启恢复（单进程重启恢复已实测）、浏览器交互、压力测试（dense/Chroma 已实测：见 optimization_report_2026-09） |

接手先检查 `git status --short`。审查前已有 Mock confidence、时间序列化、事故窗口、Demo 页面和测试等修改，以及 `tmp/` 未跟踪内容。本次保留了它们，不要误判为本轮审查已经修复的问题。

## 2. 项目结论与边界

当前最需要修改的是**诊断结果一致性、证据可追溯性和评测有效性**。模块已经足够支撑完整展示项目，增加新工具或另一套框架不能解决这些问题。

固定定位：面向工程师的故障诊断 Copilot，以日志和事故为中心，输出有来源的根因假设、影响范围、排查建议和执行记录。根因是假设，历史相似案例是参考，置信度暂不是经过校准的正确概率。

主链路：日志接入 → 事故识别/创建 → 分析任务 → 规则与取证 → Runbook/历史案例检索 → 结构化诊断 → 持久化/展示 → 人工反馈与离线评测。

默认不扩展到自动回滚、数据库切换、执行生产命令、通用聊天助手、完整 APM 平台和复杂多租户 SaaS。用户明确改变目标时，记录新范围、理由与验收后调整计划。

README 负责快速开始，DESIGN 保存设计背景，KNOWLEDGE_GUIDE 解释概念。本文件维护当前状态；历史规划不能直接当成“尚未实现”的证据。

## 3. 已实现能力：先复用，不重复建设

| 能力 | 当前实现 | 后续约束 |
|---|---|---|
| FastAPI、Dashboard、开发工具页 | `app/main.py`、`app/api/routes.py`、`templates/` | 延续现有入口 |
| 按服务接入日志 | `/logs`、`/ingest/logs`、Python logging handler | 不另建 ingest 系统 |
| 自动事故、初步时间窗口与去重 | `automatic_incident_service.py`、`incident_detector.py` | 已有但边界不完整，修正而非重做 |
| 后台任务与进度 | `analysis_job_service.py`、`AnalysisJob` | 已有，但不具备可靠队列保证 |
| 规则检测与证据选择 | `app/rule_engine/detector.py` | 用负例和混合故障改进 |
| 模式选择与工具计划 | `analysis_mode_router.py`、`diagnosis_planner.py` | 不重复添加 Planner |
| ReAct 调查分支 | `react_agent.py`、`tools.py` | 白名单与步数上限已有，补执行前置条件 |
| Markdown 分块、多查询、RRF | `runbook_chunker.py`、`query_rewriter.py`、`rrf.py` | 按消融结果开增强 |
| TF-IDF / dense / hybrid / Chroma | 两个 retriever、`embedding_service.py`、`vector_store.py` | 不新增第五种后端 |
| CrossEncoder 重排 | `embedding_service.py` | 已有可选能力 |
| Mock / 兼容 LLM / fallback | `app/llm/` | 显示实际 provider 和降级 |
| 分析、证据、Trace 持久化 | `app/models/analysis.py` | 保持单一结果契约 |
| 人工反馈 API | `feedback_service.py`、`DiagnosisFeedback` | 存取反馈不等于学习闭环 |
| Eval、Judge、消融脚本 | `eval/`、`scripts/` | 修指标可信度，不另写评测系统 |
| 故障演示业务 | `demo_shop_system/` | 围绕后端诊断闭环展示 |

历史事故检索目前读取 `data/historical_incidents.json`。未发现把新分析结果或反馈自动写回检索库的接通路径；不要宣称“系统已经从反馈持续学习”。

## 4. 本次验证记录

### 4.1 测试与离线评测

使用仓库 `.venv/Scripts/python.exe`，Mock、TF-IDF、禁用重排，开启 Hugging Face/Transformers 离线模式。未安装或升级依赖，未调用真实模型。

| 检查 | 结果 | 适用范围 |
|---|---|---|
| `python -m pytest -q` | 62 passed，2 warnings，6.45 秒 | 现有测试集合通过，不保证未覆盖场景 |
| `run_eval(..., retrieval_mode='tfidf')` | 27 案例，16 通过、11 失败 | 当前模拟数据集 |
| issue type accuracy | 92.59% | 规则输出的分类匹配 |
| severity accuracy | 92.59% | 严重程度匹配 |
| evidence recall | 92.59% | 期望关键词被证据日志覆盖 |
| Runbook recall | 77.16% | 期望来源召回 |
| Runbook Top-1 | 55.56% | 首条来源命中，当前质量短板 |
| Runbook Precision@3 | 60.49% | 前三项来源精度 |
| similar incident Top-1 | 100% | 按 issue type 匹配，不是具体事故匹配 |
| 平均离线延迟 | 54.39 ms | 本机 Mock 小数据表现，不代表模型性能 |

两条 warning 来自 Demo 的 `on_event` 弃用提示，未引起失败。独立报告写入 `runtime/audit/2026-09-08-eval.md`，该目录被 Git 忽略，换机器不一定存在；主要结果已保存在此。没有覆盖用户已修改的 `eval/reports/eval_report.md`。

失败案例完整列表：

```text
hard-cache-warning-not-incident
hard-memory-warning-without-oom
adversarial-contradictory-signals
rag-natural-language-payment-provider
rag-config-secret-database
rag-network-policy-postgres
rag-oauth-callback-login
rag-redis-secret-cache
rag-bad-release-serialization
rag-queue-lag-not-db
rag-dns-provider-timeout
```

### 4.2 隔离探针

探针使用内存 SQLite、注入客户端/集合或 mock patch，没有改动运行数据库。

| 场景 | 实测结果 |
|---|---|
| 同一个 job 调用两次 run_job | 产生 2 个 AnalysisRun |
| 持久化 Trace 时注入异常 | job=failed，但仍留下 1 个不完整 AnalysisRun |
| 同服务两批错误，第一批分析未执行 | 生成两个 Incident 和两个 job |
| 昨天的错误日志触发计数，库内有今天的 3 条错误 | 计为 4 条并触发阈值 |
| Agent 第一轮直接诊断 | 工具调用 0 次，证据为空，仍执行终止回调 |
| 字典根因列表交给 `_run_judge` | 返回 None，注入的 Judge 没有被调用 |
| 给不存在的 analysis ID 写反馈 | 默认 SQLite 下写入成功，形成孤立引用 |
| 向量集合数量等于来源数量 | 直接返回，未读取内容或调用 embedding；替身验证控制流 |

这些是问题复现，不是已经加入仓库的回归测试。修复时将对应场景纳入现有测试模块。

## 5. 问题清单与验收条件

P0：本地正确性/结果完整性阻断，先修；P1：可信度或持续运行重要问题；P2：维护与增强。安全项另标真实数据/共享部署前阻断，不把本地演示写成已发生安全事故。

“已复现”表示执行了探针或评测；“代码确认”表示控制流直接可见；“待实测”表示尚未做运行验证。**所有条目初始状态：待修复。** 行号属于审查快照，后续请按函数复核。

### F01 · P0：进度提交破坏分析结果的原子性 — **已修复（2026-09-09）**

- 证据（历史）：`app/services/analysis_service.py:279` 曾在 flush AnalysisRun 后发送 persistence 进度；`analysis_job_service._set_progress` 在同一 Session commit，把半成品 AnalysisRun 提前提交。
- 修改（已实施）：persistence 进度从提交前移到 `db.commit()` 之后，文案改过去式；分析全程的进度回调只发生在只读阶段，结果、证据、Trace 一次性原子提交。SQLite 下不另开写事务（进度更新仍走同一 Session，仅提交 job 行）。
- 验收：新增 3 项故障注入测试（第二连接观察中间状态 + Trace 写入注入失败 + run_job 端到端），并做反向验证：旧代码下 3 项全失败、新代码下全通过。全套 88 passed。
- 备注：若提交后的进度回调自身抛异常，任务会标 failed 但完整结果已落盘（可追踪，非半成品）；F03 已统一执行入口，此边界行为保持记录。

### F02 · P0：任务不幂等，缺少可靠恢复 — **已修复（2026-09-10）**

- 证据（历史）：`analysis_job_service.py:31` 曾不原子领取 pending 状态，直接设 running；API 使用进程内 BackgroundTasks；`app/main.py` 曾无恢复逻辑；初始进度提交在 try 外。
- 修改（已实施）：
  - `_try_claim` 数据库条件更新领取（仅 pending 可领取），并发执行同 job 只有一个赢家；
  - 成功任务重入不重跑，复用已有结果；初始进度提交移入 try（异常记 failed 不卡 running）；
  - `recover_interrupted_jobs` 开机清场：running→failed（写明中断原因）、pending→重新执行，经 lifespan 接入启动；
  - POST /analysis-jobs 防连点：已有 pending/running 任务时复用原任务并补发执行；完成后再次触发视为有意重分析（新建任务）。
- 验收：并发执行同 job 最多一个有效结果；中断状态恢复或明确失败；初始提交异常记 failed。新增 tests/test_f02_job_idempotency.py 7 项，全套 105 passed；旧代码下反向验证 6 项失败；临时库重启实测 running→failed（原因明确）、pending→succeeded，启动日志输出恢复摘要（运行库未动）。
- 遗留/边界：恢复语义仅适用单进程部署（多 worker 时 running 可能属于其他进程，需心跳机制）；无自动重试（重试=新建任务）；不引入独立 worker；并发 POST 先查后建仍有竞态窗口（需数据库级约束，归 F03）。

### F03 · P0：自动去重依赖尚未生成的分析结果 — **已修复（2026-09-10）**

- 证据（历史）：`incident_detector.py:68` 曾找到同 issue type 的 AnalysisRun 才认作同类；`automatic_incident_service.py:25` 创建事故、任务分开提交。
- 修改（已实施）：
  - Incident 增加 `inferred_issue_type`（迁移加列 + 从历史分析回填），去重匹配创建时保存的初步类型，不依赖未来诊断；
  - 事故与任务一次提交（`create_incident_with_job`），中途失败两者都不落库；
  - 按服务进程内锁串行化"看+建"，并发日志同一爆发只建一个事故（单进程边界）；
  - 活动任务部分唯一索引（模型声明 + 旧库迁移）：每事故最多一个 pending/running，并发先查后建由索引兜底；
  - `execute_job` 统一执行入口（后台/手动/流式共用，进度同时更新任务与流）；手动 /analyze 与 /analyze/stream 均建任务，Dashboard 经 job 感知新结果（F13 遗留收尾）；流式失败标 failed 并发 error 事件；
  - 同名服务并发注册稳定返回：主动创建重名 409，自动接入撞名归到已有服务。
- 验收：pending 时同类日志复用事故（顺序探针）；不同故障不误合并；并发同爆发单建；事故任务原子提交。新增 tests/test_f03_dedupe_and_consistency.py 10 项，全套 115 passed；旧代码下反向验证 10/10 失败；旧库结构临时库迁移冒烟通过；运行库迁移完成（10 事故全部回填类型，9 个历史无任务事故不补任务、不伪造历史）。
- 遗留/边界：进程内锁与活动任务索引覆盖单进程部署（多进程需数据库级聚合键方案）。窗口边界语义与输入时区统一已由 F04 解决（2026-09-10）：since=上一事故创建时刻正式定档，计数窗口补上界。

### F04 · P0：事件时间窗口不一致，输入时区未统一 — **已修复（2026-09-10）**

- 证据（历史）：`incident_detector.py:55` 计数只有下界，而类型推断有上界；`analysis_service.py:130` 手动事故无上界，自动事故按创建时间截止；`:136` 通过标题前缀识别来源。日志写入未显式将带时区输入统一 UTC。**修复前实测：ORM 丢偏移量存墙钟，+08:00 输入入库存成墙钟文本当 UTC 用，偏 8 小时。**
- 修改（已实施）：
  - 入账统一 UTC：`log_service.create_log_entry` 显式归一（带时区 → astimezone(UTC)；无时区 → 按 UTC 理解，写入约定），不依赖 ORM 类型隐式行为；
  - 计数窗口补上界：`evaluate_error_burst` 计数为 `[max(t-60s, since), t]` 闭区间，未来/晚到记录按自身事件时刻评估，不回头凑数（修"历史日志被未来记录凑够阈值"复现项）；
  - `received_at` 送达时间列：服务器接收时刻自动盖戳（客户端不可伪造），与事件时间区分；本轮只记+展示（API 输出），未参与判断；
  - `source` 出身列：automatic/manual，服务端按创建路径设置；分析窗口语义看出身不看标题前缀；老数据按标题回填；
  - 窗口语义明确：自动事故分析窗口 [创建-5min, 创建]（不变），手动事故同样以创建时刻封顶（修"旧手动事故重分析混入后续故障"）；下次爆发计数从上一事故创建时刻起算（F03 行为正式定档）；边界同刻算在内（闭区间）；
  - 迁移：`ensure_log_time_columns`（加 received_at 列 + 时间戳归一为无偏移 UTC 文本（与 ORM 自身写入格式一致，避免混格式比较错乱）+ 回填）与 `ensure_incident_source_column`（加列 + 按标题回填），幂等，main 启动接入。
- 验收：新增 tests/test_f04_time_semantics.py 14 项（+08:00 与 UTC 同一时刻合并计数、未来时间不凑数、晚到日志按自身窗口、边界同刻含/界外不含、极端倒序投递已知限制锁定、手动封顶不混入事后日志、出身不看标题、received_at 区分送达与发生、老库迁移加列/回填/归一）。全套 129 passed；旧代码反向验证 11/14 挂（3 过：2 项旧行为本就正确、1 项旧 bug 互相抵消，均记录在案）；运行库迁移完成（35 条日志 received_at 全回填、时间戳本已规范 0 改写；10 事故出身回填 9 manual + 1 automatic）；真实服务冒烟通过（+08:00 入账库存 UTC 12:00、API 输出北京时间 20:00、received_at 自动盖戳）。
- 遗留/边界：极端倒序投递（3 条错误完全倒着送到）在纯事件时间窗口下不触发——需水位线/乱序缓冲机制，超出本轮范围（已知限制，测试锁定语义）；received_at 暂只记录展示；历史数据中若有用 +08:00 上报的日志，其存储时间偏 8 小时且无法事后分辨（运行库 35 条全部无偏移文本、时序合理，未发现异常）。

### F05 · P0（Agent）：必要取证步骤只写在提示词里

- 证据：`react_agent.py:239` 首步可终止，最后一步强制生成；`:339` 未知动作改成 generate_diagnosis；无成功工具前置状态检查，参数未按 schema 完整验证。
- 后果：零取证也可进入诊断（**调用路径已复现，未评估真实模型答案**）；重复调用只由 prompt 禁止，工具失败成为文本后继续。
- 修改：代码记录成功执行状态，校验诊断前置条件；未知动作明确报决策错误；强类型参数及限额；不足时返回 insufficient_evidence，不用增加 MAX_STEPS 掩盖。
- 验收：首步结束、未知动作、重复参数、工具异常、非法 top_k、预算耗尽都有明确行为。
- 工作量中（Agent、测试）；收益高（防无证据诊断）。

### F06 · P1：Agent 查询未传入检索器，证据来源混用

- 证据：`analysis_service.py:473` 两个检索闭包接收 query 但未使用；`:484` 将 investigation_notes 包成 `id=0` 日志传给 LLM；notes 来自工具统计和摘要。
- 后果：Trace 看似按新查询调查，实际仍用初始上下文；派生摘要和原始日志混入同一字段；关键词搜索的匹配日志也未自然进入最终 evidence。**代码确认。**
- 修改：增加接受 query 的公开检索方法；原始日志、派生观察、历史参考分别带类型和来源 ID；结论只引用本次已收集来源。
- 验收：query 变化真正改变检索输入；调查证据可回溯 log ID；统计说明不冒充原始日志。
- 工作量中（Agent、检索接口）；收益高（调查路径与结果一致）。未发现跨会话记忆自动写回，不称其为“长期记忆被模型自言自语污染”。

### F07 · P0（评估）：Judge 调用前失败，被静默忽略 — **已修复（2026-09-09）**

- 证据（历史）：`eval/run_eval.py:102` 曾调用 `h.model_dump()`，而 `app/models/analysis.py` 的 `root_cause_hypotheses` 返回 `list[dict]`；`except Exception: return None` 把异常静默吞掉。注入 Judge 复现：非空根因下 Judge 从不执行。
- 修改（已实施）：去掉多余序列化直接传 `list[dict]`；失败返回 `{"status": "failed", "error": <脱敏>}` 不再返回 None；报告按案例写 `judge_status`/`judge_error`，汇总区写 requested/attempted/succeeded/failed/skipped 与 provider 分布（mock/llm）；judge 关闭时报告不输出 judge 行。`passed` 判定语义不变（Judge 分数为质量参考，不参与过关，避免与检索指标混淆）。
- 验收：27 例开 Judge 实测 succeeded=27/27、failed=0（修复前 27/27 静默失败），报告含 LLM Judge Summary；新增 4 项回归测试（成功路径、失败显式化+脱敏、关闭时无输出），全套 85 passed。证据：`runtime/audit/eval-f07-judge-20260909-132424.md`。
- 备注：MockJudge 启发式分数（coherence 100%、grounding 73.7%、actionability 18.77%）只作机制验证，不代表真实模型质量；真实 Judge 评测属 F10/F12 范畴。

### F08 · P1：索引按数量判断新鲜度，重建先删旧数据

- 证据：`vector_store.py:120`、`:156` 数量相同直接返回；`:138`、`:174` 先删除旧数据再 embedding/add；默认使用共享临时目录（2026-09-08 起默认改为项目内 `runtime/vector_store/chroma`，`CHROMA_PERSIST_DIR` 仍可覆盖，本条目其余部分未变）。
- 后果：内容修正但数量不变时保留旧 embedding；来源清空时保留旧集合；重建失败可失去可用索引。数量分支已用替身验证，真实 Chroma 运行未测。
- 修改：记录语料 hash、模型与分块版本；按 ID/hash 更新删除，或新集合验证后切换；缓存按项目隔离。
- 验收：同数量内容变化、删除、空库、模型切换和中断都不悄悄复用错误索引。
- 工作量中到高（索引、故障测试）；收益高（知识修正必须实际生效）。
- 2026-09-09 实操注记：chunk 类型标注修复后（数量仍 244）用 `scripts/build_vector_index.py --force`
  重建索引并实测 effective_mode=chromadb（169ms 查询），确认"改动 chunker 后必须 --force 重建"
  是实际约束；`--force` 可绕过数量分支，但"内容变化不通知"的自动新鲜度缺口仍存在。

### F09 · P1：降级信息与 Trace 不完整

- 证据：`app/llm/factory.py:16` 丢弃异常；`analysis_service.py:603` 使用未写入的 `_rewritten_variants`，provider 从环境推测；`embedding_service.py:268` 存全局最后计时，提前返回不刷新。
- 后果：改写失败仍可能标为 llm；实际 queries 没记录；并发/前次重排计时可串入另一分析。Dashboard 无独立降级标签，只能读文字 Trace。**代码确认。**
- 修改：步骤返回结构化执行元数据，记录 requested/effective mode、provider/model、fallback_reason、duration、可用的 token 用量和版本。
- 验收：制造超时和 fallback，API、页面、报告显示一致；计时不串；queries 与实际执行一致。
- 工作量中（模型、检索、持久化、页面）；收益高（结果可信度）。

### F10 · P1：JSON 合法不等于诊断有依据

- 证据：`app/llm/base.py` 的 supporting_evidence 是自由字符串；兼容客户端只做结构校验，传日志不带稳定 ID，无引用归属验证。
- 后果：可输出格式正确但不存在的证据。**验证机制缺失确认，真实模型幻觉率未测。**
- 修改：日志、chunk、历史案例稳定引用；区分事实、假设、缺失信息和建议；代码校验引用；限制输入/响应预算，日志按不可信输入处理并脱敏。
- 验收：伪造引用被拒绝或明确降级；无证据可弃答；矛盾日志保留替代假设；检索分数/Mock 置信度不冒充校准概率。
- 工作量高（端到端契约）；收益高（可验证 AI 输出）。

### F11 · P1：Runbook 质量短板已有数据

- 证据（2026-09-09 更新）：Top-1=88.89%（基线 55.56%），Recall=84.57%（基线 77.16%），P@3=74.07%，失败案例 11→9；`_run_pipeline` 多查询按 chunk ID 融合取前三，报告中同来源重复占位；retriever 可以按初始 issue type 硬过滤。
- 后果：OAuth、DNS、网络策略等具体手册缺失；通用 chunk 占有限名额；初判错误可能限制后续纠偏。**已做消融归因，证据见 `eval/reports/optimization_report_2026-09.md`。**
- 修改（已实施）：chunk 类型标注计分制（消除 "identity provider" 类误标）；查询变体带入证据摘录（旧关键词提取丢弃全小写证据词）；过滤模式 hard/soft/off 与融合参数消融（off 灾难、soft 负收益、top_k=8 负收益、RRF k 不敏感——hard + 默认参数胜出）。
- 验收：Top-1 ≥75% **达标**（88.89%）；Recall ≥85% **差 0.43 未达**（84.57%）。剩余 9 例失败中 4 例为规则/证据（范围外）、5 例检索失败（2 例跨类型硬过滤结构性排除 + 3 例稀疏词面排序/语义桥接限制），逐一有根因记录。
- 工作量中到高（评测驱动迭代）；收益高（改善实际依据）。

### F12 · P1：评测不足以支持“诊断准确率”结论

- 证据：`eval/run_eval.py:286` passed 组合类型、严重程度、关键词与来源召回；历史事故按 issue type 而非 historical_id 计分；数据是模拟集。
- 修改：区分检索、生成、运行回归；增加具体案例 ID、引用有效率、证据精度、弃答率、负例误报率、降级率与成本；调参与保留评测样本分离，人工复核标签。
- 验收：列配置/有效后端、模型/语料/数据集版本、成功错误数；全部 fallback TF-IDF 的实验不能当多个模型效果对比。**部分完成（2026-09-09）**：22 例消融 5 配置的 effective_mode 已逐一核对与请求后端一致（tfidf/dense/chromadb 真实生效），旧 95.45% 复现失败并作废；剩余指标缺口（案例 ID、证据精度、弃答率等）不变。
- 工作量中（标注、指标）；收益高（避免优化错误目标）。

### F13 · P1：Dashboard 可显示错误事故或旧结果 — **已修复（2026-09-09）**

- 证据（历史）：`templates/dashboard.html:79` 异步返回直接覆盖全局 loadedAnalysis，不检查 selectedIncident；404 直接返回，不清旧诊断；`:75` 只在未缓存时加载，不按 run ID 更新。
- 修改（已实施）：请求代次计数（analysisSeq）——响应编号对不上即丢弃；切换事故先清空面板并显示"加载中"，404 显示"该 Incident 暂无分析结果"；按 run ID 缓存（loadedAnalysisFor），job 新 run 自动重载；404 后记录已尝试的 run id 防重复请求；统计卡口径标注"最近错误日志（50 条内）"。
- 验收：node --check 语法通过；五场景竞态走查（A→B 逆序、404、新 run、网络中断自动重试、job 运行/失败）；全套 92 passed（后端无影响）。**浏览器实测待用户配合**（响应逆序需快速点击复现）。
- 遗留（已由 F03 解决，2026-09-10）：手动 analyze 现在建任务，Dashboard 经 job 感知新结果。

### F14 · P1：SSE 全量查询与模拟流式阻塞 — **已修复（2026-09-09）**

- 证据（历史）：`app/api/routes.py:78` 每连接每秒全量查询再 `[-50:]`；`/analyze/stream` 在 async 路由里同步完成分析后再 sleep 播放。
- 修改（已实施）：`list_log_entries`/`list_incidents` 支持 `limit`（倒序取前 N 再翻回升序，与旧切片同序）；`/events` 快照构建抽为 `_build_snapshot`（数据库侧限额 50），每轮新会话避免 SQLite 读锁长占；`/analyze/stream` 分析移入工作线程（复用同一 analyze_incident 执行器，不阻塞事件循环），progress_callback 经线程安全队列变实时 progress 事件，诊断文本一次性发送并标注 `simulated: true`（无真实 token 流，如实标注）。
- 验收：新增 tests/test_f14_sse_and_stream.py 6 项（limit 单测×2、快照限额、真实进度+simulated 标注、线程 ID 隔离证明、404），旧代码下反向验证 5 项失败；全套 98 passed；真实服务冒烟：/events 快照正常、/analyze/stream 实时步骤进度 + complete 事件完整。
- 注：/events 为无限流，TestClient 无法消费（starlette 已知限制），快照逻辑以函数级测试覆盖 + 真实服务冒烟。
- 剩余：SSE 每连接每秒一轮仍是轮询而非推送（本地单用户演示可接受）；真实 LLM 的 token 流不在本系统范围。

### F15 · P1：反馈存在性未校验，正向过滤忽略正确性 — **部分完成（2026-09-09）**

- 证据（历史）：`feedback_service.py:10` 曾直接 upsert；`app/database.py` 未启用 SQLite 外键检查；正向查询只看 rating，未看 is_diagnosis_correct。不存在 analysis ID 可写反馈（已复现）。
- 修改（已实施）：`upsert_feedback` 服务层校验目标 AnalysisRun 存在、不存在返回 404；并发重复提交撞唯一约束时转为更新已有行（不再 500）；`list_positive_feedback` 正向 = 高评分且 `is_diagnosis_correct=True`。
- 验收：新增 tests/test_feedback.py 4 项（404、upsert 收敛单行、5 星但判错不进正向、min_rating 边界），旧代码下反向验证 2 项判别测试失败；全套 92 passed。
- 剩余：`app/database.py` 启用 SQLite 外键检查未做——需先扫描旧库孤儿数据、评估全库写入路径风险（F02 状态变更/历史数据）后单独推进；当前服务层验票已挡住新孤儿，检索未接反馈数据（无实际污染）。

### F16 · 真实数据/共享部署前阻断：缺少身份边界 — **已修复（2026-09-10）**

- 证据（历史）：`app/api/routes.py` 日志写入、事故创建、分析触发、结果/事件读取无身份依赖，main 无身份中间件。缺少鉴权已确认；未部署公网或做攻击验证。
- 修改（已实施）：
  - 可选门锁 `app/auth.py`：`AUTH_API_KEY` 未设置/空白 = 演示模式全开放（本地行为与历史完全一致）；设置后全部接口（含 /health 与页面）经路由级依赖要求 `X-API-Key`，`secrets.compare_digest` 比较（防时序猜测），失败 401 且信息不回显钥匙；
  - 请求保护中间件 `app/middleware.py`：`RequestSizeLimitMiddleware`（Content-Length 快速拒绝 + 按实际读取字节兜底，超限 413；默认 1MB，`MAX_REQUEST_BODY_BYTES` 可调，<=0 不限）与 `WriteRateLimitMiddleware`（每 IP 每分钟写入次数，滑动窗口 + 锁，超限 429 + Retry-After；默认 600，`WRITE_RATE_LIMIT_PER_MINUTE` 可调，<=0 不限；GET/HEAD/OPTIONS 不计），经 `apply_request_protection` 挂载；
  - `/features` 如实显示 `auth_enabled`/`request_size_limit_bytes`/`write_rate_limit_per_minute`（只报状态与限额，绝不输出钥匙）；README 增加"接真实数据前"小节。
- 验收：新增 tests/test_f16_auth_and_limits.py 11 项（未设钥匙全开放、无/错钥匙 401、对钥匙 200、401/429 不回显钥匙、面板如实显示不泄钥匙、413 大小上限、429 频率上限 + Retry-After、读取不占额度、零值关闭限流）。全套 140 passed；旧代码反向验证 9/11 失败（2 过：演示模式全开放为锁定行为、旧代码全放行导致"对钥匙 200"必然通过，均记录）；真实服务冒烟通过（带锁启动：无钥匙 401、对钥匙 200、600 字节包对 300 限额 413、第三次写入 429 + retry-after 59、读取不受限、面板无钥匙泄漏，冒烟数据已清理）。
- 遗留/边界：单把钥匙不分角色（多租户/RBAC 明确不做，基线原则）；限流状态在进程内存（重启清零、多 worker 各算各的）；不信任 X-Forwarded-For；被 413/401 拒绝的写入尝试同样计入频率额度（防刷按设计）；未做公网部署或攻击验证。

### F17 · P2：配置、依赖与文档状态分散

- 证据：各模块散读环境变量，有些导入时固定；默认依赖含重型检索包且部分开放下界；README 建议 `.env` 但普通命令不加载它，应用无 dotenv 调用；DESIGN 把已有异步任务、向量检索和反馈列为 Future Work。
- 修改：小型统一配置校验，区分启动/请求配置；记录 Python 与可复现依赖，基础/可选依赖分组；明确配置加载；历史文档指向本基线。
- 验收：新环境可运行 Mock/TF-IDF，坏配置明确报错；不打印密钥，不借此自动升级全部包。
- 工作量中；收益中（减少启动差异）。本轮只补了文档入口，完整配置治理未做。

### F18 · P2：日志接入会等待网络

- 证据：`integrations/python_logging_handler.py:37` 每条日志同步新建 HTTP client，默认 timeout=2 秒，未传 record.created 原始时间。
- 后果：故障时业务线程等待上报；反复连接增加成本，发生时间变成接收时间。**代码确认，压力场景待测。**
- 修改：真实接入需要有界队列、批处理/连接复用、丢弃统计、关闭行为和原始事件时间；保持 Demo 轻量。
- 验收：接收端不可用不把业务拖到秒级；缓冲有界、丢弃可观测。
- 工作量中；收益中，真实接入时升级优先级。

## 6. AI 执行链十二层审计

| 层 | 当前判断 | 动作 |
|---|---|---|
| 系统提示词 | 有顺序规则，代码门禁不足 | F05 |
| 会话历史 | history 与 recent observations 重复注入 | 去重、来源、输入预算 |
| 长期记忆 | 静态文件，无自动写回路径 | 不新增记忆系统 |
| 蒸馏 | 无独立长期记忆蒸馏流程 | 不虚构缺陷 |
| 主动召回 | 检索与多查询已存在 | F06/F11 |
| 工具选择 | 过早终止，未知动作变诊断 | F05 |
| 工具执行 | 白名单已有；query 未使用，异常文字化 | F05/F06 |
| 工具解释 | 派生统计混入 evidence_logs | F06/F10 |
| 答案结构 | 有类型校验，缺引用真实性验证 | F10 |
| 平台展示 | 异步身份竞态、模拟流式 | F13/F14 |
| 额外模型/降级层 | 改写、决策、诊断、Judge 分别调用，降级信息不足 | F07/F09，显式预算 |
| 持久化 | 半成品、重复 job、过期索引 | F01/F02/F08 |

先保证输入窗口、工具执行、证据类型和存储正确，再比较模型。不能把这些问题归因于“大模型不够聪明”。

## 7. 改进路线与完成门槛

| 阶段 | 范围 | 完成门槛 | 暂不引入 |
|---|---|---|---|
| A：结果可靠 | F01→F02/F03→F04；F07 可单独小修 | 半成品/重复任务/待分析去重/时间边界回归；Judge 确实执行且失败可见 | 新框架、新接入源 |
| B：诊断可信 | F05/F06/F09/F10、F13 | 可弃答、引用可核验、参数确实使用、降级醒目、页面身份一致 | 多 Agent、长记忆 |
| C：RAG 可衡量 | F08/F11/F12 | 索引更新可靠，固定评测与消融，硬例改善且旧例不退化 | 新向量库、微调 |
| D：演示可持续 | F14/F15/F17，必要时 F18 | 新环境可启动，日志查询有上限，反馈状态完整 | 全面前端重构 |
| E：真实内部试用 | F16、恢复实测、脱敏与接入 | 权限/恢复/隔离验证，有真实样本与人工对照 | 宣称生产级、自动操作生产 |

每阶段分小改动完成，不做一次大重构。新增依赖必须说明解决哪个已验证问题、现有模块为何不足、如何量化收益及撤回。

## 8. 每次工作或运行前检查

1. 完整读取本文件，检查接续状态，用相关源码重新核对结论。
2. 查看 `git status --short`，辨认用户修改、未跟踪内容与本次编辑范围。
3. 写清一句主目标，如“修 F01 半结果提交”，列验收条件和涉及模块。
4. 从能力表找复用位置，先搜索函数/接口，不先新建 v2 或平行 Agent。
5. 用户的新需求不在计划中时，记录范围与理由，不擅自连带实现整个待办。
6. 确认数据库路径、provider、检索模式、自动事故开关、端口与外部请求范围。
7. 隔离验证，真实 key 不打印，运行库不用作测试库，已有报告不直接覆盖。
8. 修改后跑相关测试；主链路/跨模块契约变化再跑完整测试与相关 Eval。
9. 检查 diff，交代修改、验证和限制，更新第 1 节、问题状态与第 10 节。

普通启动前不用每次重复全部测试，但须确认已有验证对应当前代码和配置，已知限制可接受。功能改变后不能拿旧测试结果冒充新验证。

### PowerShell 隔离运行参考（仓库根目录）

建议单独终端测试。环境变量只影响当前终端及子进程；真实模型演示另开终端显式设置。

```powershell
$env:LLM_PROVIDER = 'mock'
$env:RETRIEVAL_MODE = 'tfidf'
$env:ANALYSIS_MODE = 'pipeline'
$env:CROSS_ENCODER_ENABLED = '0'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
./.venv/Scripts/python.exe -m pytest -q
```

沿用上述环境，评测不覆盖已跟踪报告：

```powershell
@'
from datetime import datetime
from pathlib import Path
from eval.run_eval import run_eval
stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
report = run_eval(
    report_path=Path('runtime/audit') / f'eval-{stamp}.md',
    retrieval_mode='tfidf',
)
print(report['metrics'])
print([case['case_id'] for case in report['failed_cases']])
'@ | ./.venv/Scripts/python.exe -
```

沿用 Mock 环境启动新演示库：

```powershell
$demoStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$env:DATABASE_URL = "sqlite:///./runtime/data/demo-$demoStamp.db"
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

第二终端：

```powershell
$env:INCIDENT_API_URL = 'http://127.0.0.1:8010'
./.venv/Scripts/python.exe -m uvicorn demo_shop_system.app:app --host 127.0.0.1 --port 8020
```

工程师台 `http://127.0.0.1:8010`，业务 Demo `http://127.0.0.1:8020`。端口占用先确认服务，再换端口并同步 INCIDENT_API_URL；不要清数据库或停止不明进程。

应用读进程环境变量。仅创建 `.env` 不会使普通启动命令加载它；选择文件方式需显式加载，例如支持依赖已安装时用 uvicorn `--env-file .env`。不要在报告展示文件内容。

## 9. 防止过度新增与偏离方向

- 先修失败场景再论证新能力；无明确用户需求或可验证问题，不增加抽象层。
- 不为好看指标删除 hard cases、随意放宽标签，或把 fallback 当目标后端成绩。
- “工具声明了”“返回 JSON”“测试通过”不等于真实取证、可信诊断或可生产部署。
- 检索、证据选择、响应整形明确归属；迁移时说明旧路径撤除条件，不长期维护两套主链路。
- 历史案例、工具摘要与当前日志分开，不让未经人工确认的评分自动成为新知识。
- API/DB/诊断 schema 变化考虑旧库与页面，不只修返回 JSON。
- 保持 FastAPI + SQLAlchemy + SQLite 原型架构，实际并发/任务/部署需求证明必要时再迁移设施。
- 用户批准新方向可以改变计划，每次记录原因、影响、验收和回退，不依赖聊天上下文记忆。

通过根目录 `AGENTS.md` 提醒支持该文件的编码助手先读，README 提供人工入口。**未添加启动钩子，业务程序不会自动阅读 Markdown，也不能保证不支持 AGENTS.md 的工具执行。** 换工具时手动要求先读本文件。

## 10. 决策与交接记录

| 日期 | 完成/决策 | 原因与验证 | 下一步 |
|---|---|---|---|
| 2026-09-08 | 建立基线，保留主链路，暂缓新增框架；仅修改文档入口 | 62 测试通过，27 案例 11 失败，8 类隔离探针确认缺口 | 优先 F01；用户可调整顺序 |
| 2026-09-08 | 文件结构中等整理（用户批准）：git 卫生、移除空壳 app/tracing、Chroma 默认目录项目化、模板绝对路径、清理脚本去过期项；分三笔主题提交 f373abf/d19f660/结构整理 | 62 passed 与基线一致；get_chroma_persist_dir 默认与覆盖实测通过；仓库外目录启动 smoke test 三端点均 200；清理脚本 dry run 正常 | F01-F18 状态不变；F08 仅默认目录落地，数量新鲜度与先删后建仍按 C 阶段；下一步按第 7 节 A 阶段 |
| 2026-09-09 | Runbook 检索重优化（用户批准计划，全配置消融主战场）：4 个杠杆实施 + 逐轮数据裁决；保留 hard 过滤与默认融合参数；RUNBOOK_FILTER_MODE/PIPELINE_VARIANT_TOP_K/RRF_K 保留为环境配置项（默认值=历史行为）；旧 95.45% 复现失败正式作废 | 71 passed（+9 标注回归）；27 例 Top-1 88.89%/Recall 84.57%/P@3 74.07%；22 例消融 tfidf 单查询 Top-1 100%、5 配置 effective_mode 全部与请求后端一致；4 后端对比 hybrid 92.59% | F11 验收：Top-1 ≥75% 达标、Recall ≥85% 差 0.43；剩余 5 例检索失败已逐一归因（2 跨类型结构性 + 3 稀疏词面限制）；F12 有效后端验证部分完成；F01/F02/F03/F04/F07 不变，下一步 F01 |
| 2026-09-09 | 修复评测 Judge 静默失效（F07，用户按"小步消化"节奏批准）：`_run_judge` 去掉对 list[dict] 的 `model_dump()` 调用、失败不再返回 None；报告按案例写 judge_status/judge_error，汇总写 requested/attempted/succeeded/failed/skipped 与 provider；新增 `_desensitize_error`（URL/长 token 脱敏）；`passed` 判定语义保持不变 | 新增 tests/test_eval_judge.py 4 项，全套 85 passed；27 例开 Judge 实测 succeeded=27/27（修复前 27/27 静默失败），证据 runtime/audit/eval-f07-judge-20260909-132424.md | F07 标记已验证完成；下一步按用户节奏 F01（分析结果事务原子性） |
| 2026-09-09 | 修复分析结果原子性（F01，用户批准）：persistence 进度消息从 flush 后移到 `db.commit()` 之后（文案改过去式），进度回调在分析全程只于只读阶段触发；结果、证据、Trace 一次提交 | 新增 tests/test_analysis_transaction.py 3 项（第二连接中间状态观察、Trace 注入失败回滚、run_job 端到端失败）；反向验证旧代码下 3 项全失败；全套 88 passed | F01 标记已验证完成；下一步按用户节奏 F15 或 F13 |
| 2026-09-09 | 修复反馈完整性（F15，用户批准）：upsert 服务层校验目标存在（404）、并发撞唯一约束转更新、正反馈 = 高评分 + 判定正确；SQLite 外键开关本轮不做（需先扫旧库孤儿数据，F15 剩余项） | 新增 tests/test_feedback.py 4 项，旧代码下反向验证 2 项判别测试失败；全套 92 passed | F15 标记部分完成（外键启用留待旧数据扫描后）；下一步按用户节奏 F13 |
| 2026-09-09 | 修复 Dashboard 竞态（F13，用户批准）：analysisSeq 请求编号丢弃过期响应；切换即清空面板并显式"加载中"；按 run id 缓存、job 新 run 自动重载；404 空态 + 防重复请求；统计卡标注 50 条口径 | 验证：node --check 语法通过；五场景竞态走查；全套 92 passed（纯前端改动）；浏览器实测待用户配合（无 JS 测试基建，未做反向验证） | F13 标记已修复（浏览器实测为收尾）；下一步建议 F14（SSE 全量查询）或 F02/F03/F04 |
| 2026-09-09 | 修复 SSE 全量查询与模拟流式（F14，用户批准）：list_* 加 limit 参数、/events 快照抽 _build_snapshot 数据库侧限额 50；/analyze/stream 分析移工作线程（同一执行器）+ 进度经线程安全队列实时上报 + 诊断文本标注 simulated: true | 新增 tests/test_f14_sse_and_stream.py 6 项，旧代码下反向验证 5 项失败；全套 98 passed；真实服务冒烟通过（实时进度/complete/simulated 均验证）；TestClient 无法消费无限流（starlette 限制），快照逻辑函数级测试覆盖 | F14 标记已修复；下一步建议 F02/F03/F04 或 F16 |
| 2026-09-10 | 修复任务幂等与启动恢复（F02，用户批准）：`_try_claim` 原子领取（条件更新，仅 pending 可领）；成功任务重入不重跑；初始进度提交移入 try；`recover_interrupted_jobs` 开机清场（running→failed 写明原因、pending→重新执行）经 lifespan 接入；POST /analysis-jobs 防连点复用未完成任务；重试语义=新建任务，无自动重试 | 新增 tests/test_f02_job_idempotency.py 7 项，旧代码下反向验证 6 项失败（1 项语义记录测试新旧一致）；全套 105 passed；临时库重启实测 running→failed、pending→succeeded、启动日志输出恢复摘要（运行库未动） | F02 标记已修复；遗留（并发先查后建唯一约束、手动 analyze 建 job、多 worker 心跳）归 F03；下一步建议 F03 |
| 2026-09-10 | 修复事故去重与任务一致性（F03，用户批准）：Incident 存 `inferred_issue_type`（迁移加列+历史回填），去重不依赖分析结果；事故+任务一次提交；按服务进程内锁防并发双建；活动任务部分唯一索引（模型声明+旧库迁移）；`execute_job` 统一执行入口（后台/手动/流式共用）；手动 /analyze 与 stream 建任务（失败标 failed + error 事件）；服务重名 409/归已有 | 新增 tests/test_f03_dedupe_and_consistency.py 10 项，旧代码下反向验证 10/10 失败；全套 115 passed；旧库结构临时库迁移冒烟通过（加列/回填/索引生效）；运行库迁移完成（10 事故全部回填类型，9 个历史无任务事故不补任务） | F03 标记已修复；遗留（多进程聚合键方案、窗口边界语义）归 F04；下一步建议 F04 |
| 2026-09-10 | 修复日志时间语义（F04，用户批准）：入账统一 UTC（`create_log_entry` 显式归一，实测旧代码 +08:00 输入丢偏移量偏 8 小时）；计数窗口补上界 `[max(t-60s, since), t]` 闭区间；`received_at` 送达时间列（服务器盖戳+展示）；`source` 出身列代替标题判断（手动分析窗口同样以创建时刻封顶）；迁移 `ensure_log_time_columns`/`ensure_incident_source_column`（幂等，启动接入） | 新增 tests/test_f04_time_semantics.py 14 项；全套 129 passed；旧代码反向验证 11/14 失败（3 过：naive 按 UTC 与边界同刻旧行为本就正确、+08:00 同刻合并系旧双 bug 抵消，均记录）；运行库迁移完成（35 条日志 received_at 全回填、时间戳本已规范 0 改写；10 事故出身 9 manual + 1 automatic）；真实服务冒烟（+08:00 入账库存 UTC 12:00、received_at 自动盖戳、启动无报错，冒烟数据已清理） | F04 标记已修复；**A 路线（结果可靠）全线收工**；下一步建议 F16（真实数据/共享部署前安全边界） |
| 2026-09-10 | 修复接入安全边界（F16，用户批准）：可选接入钥匙（`AUTH_API_KEY` 未设=演示全开放，设置后全接口要求 `X-API-Key`，compare_digest 防时序、401 不泄钥匙）；请求大小上限（Content-Length 快速拒绝 + 实际字节兜底，413）与写入频率限流（每 IP 滑动窗口，429 + Retry-After，读取不计，零值关闭）；`/features` 如实显示门锁/限额状态；README 增"接真实数据前"小节 | 新增 tests/test_f16_auth_and_limits.py 11 项；全套 140 passed；旧代码反向验证 9/11 失败（2 过：演示模式全开放为锁定行为、旧代码全放行使"对钥匙 200"必然通过）；真实服务冒烟（带锁启动：无钥匙 401/对钥匙 200/超包 413/第三次写入 429+retry-after 59/读取不受限/面板无钥匙泄漏，冒烟数据已清理） | F16 标记已修复；**P0 全部收工**；下一步建议 F10/F12 真实模型评测剩余指标或 F15 剩余（SQLite FK pragma） |

每次工作更新此模板，不另建竞争性总计划：

```text
日期：
目标/问题编号：
涉及模块与复用：
实际修改：
验证命令与结果（mock/真实模型、有效检索模式）：
问题状态变化（待修复/进行中/已验证完成/暂缓及理由）：
新决策或偏离原计划的理由：
限制与下一步：
```

原始复现场景不再出现、相关回归通过、契约和文档同步，才标记“已验证完成”。本轮审查不自动赋予任何问题该状态。
