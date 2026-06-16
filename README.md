# AI Incident Copilot Platform

## 实时接入模式

当前版本支持自动日志接入、Incident 检测、Analysis Job、SSE 实时状态和监控 Dashboard。

启动平台：

```powershell
$env:DATABASE_URL="sqlite:///$($env:TEMP.Replace('\','/'))/incident-live.db"
uvicorn app.main:app --reload --port 8000
```

启动独立的测试支付服务：

```powershell
$env:INCIDENT_API_URL="http://127.0.0.1:8000"
uvicorn demo_payment_service.app:app --reload --port 8001
```

制造一次数据库故障并请求支付：

```powershell
curl.exe -X POST http://127.0.0.1:8001/faults/database
curl.exe -X POST http://127.0.0.1:8001/payments
```

访问 `http://127.0.0.1:8000`，页面会实时显示日志、自动 Incident、Analysis Job 进度和完整诊断。人工构造数据的入口位于 `http://127.0.0.1:8000/dev-tools`。

Python 应用和 Fluent Bit 的接入方式见 `integrations/README.md`。

面向 AIOps 场景的智能故障诊断后端系统。

本项目围绕 Incident Analysis Pipeline，结合规则信号检测、证据日志提取、Runbook Retrieval、可插拔 LLM 结构化诊断、Trace 和离线 Eval Harness，演示一次事故从日志分析到诊断结果生成的完整后端流程。

项目当前定位是可解释、可评测的 Incident Copilot 原型，不是完整 AIOps 平台，也不是能够自主操作生产环境的 Fully Autonomous Agent。

## 项目简介

当业务服务发生事故后，工程师通常需要从大量日志中识别异常信号、寻找证据、查阅排障手册，并整理可能原因和建议动作。

本项目以 Incident 为分析对象，通过现有日志和 Runbook 知识库生成初步诊断结果：

- 使用 Rule Engine 从日志中识别故障类型。
- 提取支持诊断结论的 Evidence Logs。
- 检索与事故上下文相关的 Runbook Chunks。
- 默认使用 Mock LLM，也可选择 OpenAI-compatible Provider 生成结构化诊断结果。
- 使用 Trace 记录分析流程。
- 使用 Eval Harness 离线评估分析效果。

## 项目背景

普通日志查询只能告诉工程师“发生了什么”，但真实故障排查还需要回答：

- 这次事故可能属于什么问题？
- 哪些日志支持当前判断？
- 应该参考哪些排障手册？
- 可能的影响范围是什么？
- 下一步应该检查什么？
- 分析流程具体执行了哪些步骤？

本项目通过一个受控的分析 Pipeline，模拟 AI Incident Copilot 后端如何组织这些信息，并为后续接入真实 LLM、更多信号源和更完整评测能力提供基础。

## 核心能力

- **Incident Analysis Pipeline**：围绕某个 Incident 执行完整分析流程。
- **Rule-based Signal Detection**：根据日志关键词识别数据库、超时、鉴权、缓存、内存和服务器错误等信号。
- **Evidence Logs**：记录支持故障判断的关键日志。
- **Runbook Retrieval**：根据事故标题、服务名、故障类型和证据日志检索相关排障文档片段。
- **Pluggable LLM Structured Diagnosis**：默认使用 Mock LLM，可选 OpenAI-compatible Provider，并支持失败 fallback。
- **Analysis Trace**：记录日志筛选、规则检测、证据选择、Runbook 检索和摘要生成步骤。
- **Offline Eval Harness**：使用模拟事故数据评估故障类型、严重程度、证据召回和 Runbook 召回效果。

## 技术栈

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- TF-IDF
- sentence-transformers
- Markdown Runbooks

## 核心流程

```text
事先登记 Service 和准备 Runbooks
  ↓
服务运行过程中持续产生并写入 Logs
  ↓
发现问题后创建 Incident
  ↓
调用 POST /incidents/{incident_id}/analyze
  ↓
根据 Incident.service_id 查询相关日志
  ↓
Rule Engine 检测 issue_type、severity 和 evidence_logs
  ↓
Runbook Retrieval 检索相关文档片段
  ↓
LLM Client 生成结构化诊断
  ↓
保存 AnalysisRun、IncidentEvidence 和 AnalysisTrace
  ↓
返回分析结果
```

## 示例场景

假设系统已经登记了：

```text
Service: payment-service
```

服务运行时出现日志：

```text
ERROR DBConnectionTimeout while connecting to mysql-primary
ERROR Payment API returned 500 after mysql-primary connection retry failed
```

随后创建 Incident：

```text
Payment API returns 500 errors
```

调用 Analyze 后，系统可能得到：

```text
Issue Type: database_issue
Severity: high
Evidence: DBConnectionTimeout / mysql-primary 相关日志
Runbook: database_issue.md 相关片段
Diagnosis: payment-service 可能受到数据库连接问题影响
Suggested Actions: 检查 mysql-primary 健康状态、连接数和连接池
```

## 快速开始

创建虚拟环境：

```powershell
python -m venv .venv
```

激活虚拟环境：

```powershell
..venv\Scripts\Activate.ps1
```

如果虚拟环境创建在当前项目根目录，也可以使用：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

启动 FastAPI：

```powershell
uvicorn app.main:app --reload
```

启动后可以访问：

```text
http://127.0.0.1:8000/docs
```

## 一键 Demo

先在一个终端中启动 API：

```powershell
uvicorn app.main:app --reload
```

再打开另一个终端运行：

```powershell
python scripts/demo_incident_analysis.py
```

Demo 会自动：

1. 创建或复用 `payment-service`。
2. 插入 `DBConnectionTimeout` 和 `mysql-primary` 相关日志。
3. 创建 `Payment API returns 500 errors` Incident。
4. 调用现有 Analyze Pipeline。
5. 打印 Evidence Logs、Runbook Chunks、结构化诊断和 Trace。

## 运行测试

```powershell
pytest
```

测试覆盖 API、Rule Engine 分析、Runbook Retrieval、Mock/Fallback LLM 结构化诊断、Trace 和 Eval Harness。

## 运行离线评测

```powershell
python eval/run_eval.py
```

Eval Harness 会读取 `eval/eval_cases.json`，对模拟事故逐条运行 Analyze Pipeline，并生成：

```text
eval/eval_report.md
```

当前评测指标包括：

- `issue_type_accuracy`
- `severity_accuracy`
- `evidence_recall`
- `runbook_retrieval_recall`
- `average_latency_ms`

## Runbook Retrieval

Runbook 文档存放在：

```text
runbooks/
```

系统会先按照 Markdown Heading 和段落将文档切成 Chunks，再根据以下信息构造检索 Query：

- Incident Title
- Service Name
- Issue Type
- Evidence Logs

当前默认使用 TF-IDF Retrieval：

```text
backend=tfidf
```

项目同时支持 sentence-transformers 语义向量检索，可以通过环境变量启用：

```powershell
$env:RUNBOOK_EMBEDDING_BACKEND="sentence-transformers"
```

默认模型为：

```text
sentence-transformers/all-MiniLM-L6-v2
```

如果 `sentence-transformers` 依赖或模型不可用，系统不会中断 Analyze Pipeline，而会自动 fallback 到 TF-IDF。

## 当前限制

- 默认 LLM Provider 是 **Mock LLM**；真实 OpenAI-compatible Provider 是可选能力，效果取决于所配置的模型和服务。
- 当前系统只负责诊断、证据展示和建议，不执行自动修复、自动回滚或生产环境操作。
- 当前 Eval Cases 和 Runbooks 均为模拟数据，评测结果不能代表真实生产事故诊断准确率。
- 当前 Agent 能力属于受控的 Agentic Workflow / Pipeline，不是 Fully Autonomous Agent。
- 当前没有前端页面，主要通过 FastAPI `/docs`、Demo Script 和 Eval Report 展示能力。
- 当前日志主要通过 `POST /logs` 模拟写入，尚未接入真实日志采集平台。
- 当前分析会查询同一服务已有日志，尚未实现严格的 Incident 时间窗口过滤。
- 当前 Runbook Retrieval 未接入独立向量数据库。

## 后续规划

- 扩展更多真实 LLM Provider，并加强结构化输出和证据引用评测。
- 为 Incident 增加时间窗口，减少无关历史日志干扰。
- 增加更复杂的 Eval Cases、干扰文档和检索评测指标。
- 支持 Runbook Chunk Embedding 缓存和向量数据库。
- 扩展 Metrics、Alerts、Deployment Events 等故障信号。
- 增加相似历史 Incident Retrieval。
- 增加人工反馈和诊断结果评估闭环。

项目后续仍将保持 Copilot 定位：帮助工程师分析事故和整理建议，而不是替代工程师自动操作生产系统。

## 可选真实 LLM

项目默认使用 Mock LLM，因此本地运行、测试和离线评测都不依赖真实大模型 API。

如需启用 OpenAI-compatible Provider，可在当前终端设置：

```powershell
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_API_KEY="<your-api-key>"
$env:LLM_BASE_URL="https://your-provider.example/v1"
$env:LLM_MODEL="your-model-name"
```

不要将 API Key 写入代码、README、测试文件或提交到 Git。

真实 LLM 会接收 Incident、Severity、Evidence Logs、Runbook Chunks 和 Similar Incidents，并返回经过 Schema 校验的结构化诊断。如果调用失败、JSON 无法解析或 Schema 校验失败，系统会自动 fallback 到 Mock LLM，并在 Trace 中记录 `provider=mock_fallback`。
