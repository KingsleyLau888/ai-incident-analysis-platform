# AI Incident Copilot Platform

> **开发或运行前先读：[项目基线与改进指南](docs/PROJECT_BASELINE.md)。** 其中记录已实现能力、审查问题、修复顺序、运行检查和交接状态。编码助手入口见 [AGENTS.md](AGENTS.md)。

面向 AIOps 场景的智能故障诊断后端原型。项目模拟一个业务系统持续产生日志，AI Incident Copilot 接收日志、自动创建 Incident、执行分析流程，并输出可解释的诊断结果。

当前项目不是完整生产级 AIOps 平台，也不是 fully autonomous Agent。它更准确的定位是：一个可运行、可评测、可展示的 Incident Analysis Pipeline，包含规则检测、证据日志、Runbook RAG、相似历史事故检索、可插拔 LLM 结构化诊断、Trace 和 Eval Harness。

## 核心能力

- 日志接入：业务系统通过 API / logging handler 把日志发送到平台。
- Incident 自动创建：检测到错误日志后自动创建待分析事故。
- Rule Engine：根据日志信号识别 `database_issue`、`timeout_issue`、`auth_issue` 等故障类型。
- Evidence Logs：提取支撑判断的关键日志。
- Runbook Retrieval：从 Markdown runbooks 中检索相关排障片段。
- Similar Incident Retrieval：检索相似历史事故，辅助判断根因和处理建议。
- Agent-like Analysis：复杂事故可走 ReAct-style 分析步骤，Trace 中记录每一步。
- LLM Structured Diagnosis：默认 Mock LLM，可选 OpenAI-compatible Provider，例如 DeepSeek。
- Eval Harness：离线评测 issue type、evidence、runbook retrieval、similar incident retrieval 等指标。

## 技术栈

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- TF-IDF
- sentence-transformers
- ChromaDB
- OpenAI-compatible LLM API

## 核心流程

```text
业务系统运行
  -> 产生业务日志 / 错误日志
  -> 日志发送到 AI Incident Copilot
  -> 平台自动创建 Incident
  -> analyze pipeline 读取同一 service 的相关日志
  -> rule_engine 判断 issue_type / severity / evidence_logs
  -> 根据事故复杂度选择 pipeline 或 agent-like 分析路径
  -> 检索 runbook chunks
  -> 检索 similar incidents
  -> LLM client 生成结构化诊断
  -> 保存 analysis result 和 trace
  -> Dashboard 展示结果
```

## 示例场景

以 `demo-shop-checkout-service` 为例：

1. 用户在 Shop 页面点击 checkout。
2. Shop 后端正常写入订单、库存、支付日志。
3. 开启“数据库故障”后，checkout 过程产生：

```text
DBConnectionTimeout while connecting to shop-primary
Order creation failed because shop-primary database is unavailable
Checkout API returned 500 after database write failure
```

4. AI Incident Copilot 自动创建 Incident。
5. 系统分析出：

```text
Issue Type: database_issue
Severity: high
Root Cause Hypotheses: shop-primary database connection/network issue
Suggested Actions: inspect database health, connection pool, network policy
```

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动 Incident Copilot 后端：

```powershell
uvicorn app.main:app --reload --port 8000
```

访问：

```text
Dashboard: http://127.0.0.1:8000
API Docs:  http://127.0.0.1:8000/docs
Dev Tools: http://127.0.0.1:8000/dev-tools
```

## Demo Shop

终端 1，启动 Incident Copilot：

```powershell
$env:DATABASE_URL="sqlite:///$($env:TEMP.Replace('\','/'))/incident-live.db"
uvicorn app.main:app --reload --port 8010
```

终端 2，启动模拟电商系统：

```powershell
$env:INCIDENT_API_URL="http://127.0.0.1:8010"
uvicorn demo_shop_system.app:app --reload --port 8020
```

访问：

```text
Shop 用户页面: http://127.0.0.1:8020
工程师监控台: http://127.0.0.1:8010
```

在 Shop 页面点击“数据库故障”“支付超时”“认证失败”后再 checkout，就能看到日志、Incident、Analysis Job 和诊断结果自动更新。

## 命令行 Demo

```powershell
uvicorn app.main:app --reload
python scripts/demo_incident_analysis.py
```

这个脚本会创建一个 `payment-service` 风格的示例，插入 `DBConnectionTimeout` / `mysql-primary` 相关日志，创建 `Payment API returns 500 errors` incident，并打印完整分析结果。

## Runbook Retrieval

Runbook 文档放在：

```text
runbooks/
```

系统会把 Markdown 文档切成 chunks，再根据 incident title、service name、issue type 和 evidence logs 构造查询。

当前支持多种 retrieval mode：

```powershell
$env:RETRIEVAL_MODE="tfidf"
$env:RETRIEVAL_MODE="sentence-transformers"
$env:RETRIEVAL_MODE="hybrid"
$env:RETRIEVAL_MODE="chromadb"
```

默认建议本地开发使用 `tfidf`，稳定、无需模型下载。启用 `sentence-transformers` 或 `chromadb` 时，如果模型不可用，系统会 fallback 到可运行的检索方式。

## LLM Provider

默认使用 Mock LLM，保证本地测试不依赖真实 API。

可选接入 DeepSeek 或其他 OpenAI-compatible Provider：

```powershell
$env:LLM_PROVIDER="openai_compatible"
$env:LLM_API_KEY="your_api_key"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-chat"
```

不要把真实 API key 提交到 GitHub。建议写在本地 `.env` 中，`.env` 已被 `.gitignore` 忽略。

## 运行测试

```powershell
pytest
```

## 运行离线评测

```powershell
python eval/run_eval.py
```

报告默认输出到：

```text
eval/reports/eval_report.md
```

RAG 对比实验：

```powershell
python scripts/rag_ablation_benchmark.py
```

## 目录结构

```text
app/                  核心后端代码
data/                 历史事故模拟数据
demo_shop_system/     可交互电商 demo
docs/                 项目说明文档
eval/                 离线评测用例和报告
integrations/         日志接入示例
runbooks/             Runbook 知识库
scripts/              Demo、benchmark、索引构建脚本
templates/            Dashboard 页面模板
tests/                pytest 测试
runtime/              本地运行数据库和临时产物，不提交 Git
```

更详细的目录说明见 `docs/PROJECT_STRUCTURE.md`。

## 当前限制

- 当前系统只做诊断和建议，不做自动修复。
- Mock LLM 是模板化诊断，不等于真实大模型能力。
- OpenAI-compatible LLM 是可选能力，失败时会 fallback。
- Runbooks、historical incidents、eval cases 都是模拟数据。
- Agent 能力是受控的 agent-like workflow，不是任意自主操作生产环境的 Agent。
- 当前 Dashboard 用于演示后端流程，不是完整运维产品前端。

## 后续规划

以下为历史方向列表，其中时间窗口、去重、重排等已有基础实现。当前待办和验收以 [项目基线](docs/PROJECT_BASELINE.md) 为准，不应直接视为尚未实现的新功能。

- 接入更真实的日志源，例如 OpenTelemetry、Fluent Bit、Prometheus Alertmanager。
- 增加时间窗口、去重、告警聚合和 incident lifecycle。
- 引入 reranking 和更系统的 RAG benchmark。
- 扩充 runbooks、历史事故库和 hard eval cases。
- 增强 Trace 可视化，让每一步证据来源更清楚。
