# Project Structure

这个文件用于解释项目目录，帮助快速区分：核心源码、Demo 系统、知识库、评测、文档和本地运行产物。

## 根目录

```text
README.md              GitHub 展示与快速开始
DESIGN.md              项目定位与架构设计
requirements.txt       Python 依赖
pytest.ini             pytest 配置
.env.example           环境变量模板，不包含真实密钥
.env                   本地真实环境变量，已被 .gitignore 忽略，不要提交
```

## 核心后端

```text
app/
```

AI Incident Copilot 的 FastAPI 后端主程序。

```text
app/main.py
```

FastAPI 应用入口，注册 API、页面路由和数据库初始化。

```text
app/api/
```

API 路由层，负责 HTTP 请求入口，例如服务、日志、Incident、Analyze、Dashboard、SSE。

```text
app/services/
```

业务逻辑层。项目最核心的流程在这里，例如日志保存、Incident 检测、analysis pipeline、Runbook Retrieval、Similar Incident Retrieval、ChromaDB VectorStore、Eval 辅助逻辑。

```text
app/rule_engine/
```

规则信号检测，根据日志关键词判断 `database_issue`、`timeout_issue`、`auth_issue` 等故障类型。

```text
app/agent/
```

Agent 相关逻辑，包括 analysis mode router、ReAct Agent、工具定义。它是复杂事故分析的增强路径，不是自动修复 Agent。

```text
app/llm/
```

LLM client 层，包括 Mock LLM、OpenAI-compatible client、factory 和 fallback。

```text
app/models/
```

SQLAlchemy 数据库模型，也就是数据库表结构。

```text
app/schemas/
```

Pydantic API schema，也就是请求和响应的数据结构。

## Demo 与接入

```text
demo_shop_system/
```

模拟真实电商 checkout 系统。用户操作会产生业务日志，并发送给 AI Incident Copilot。

```text
integrations/
```

日志接入示例，例如 Python logging handler、Fluent Bit 配置。

```text
templates/
```

Dashboard / Dev Tools 页面模板。

## RAG 知识库

```text
runbooks/
```

Runbook 排障文档。系统会把 Markdown 文档切成 chunks，用于 Runbook Retrieval。

```text
data/historical_incidents.json
```

模拟历史事故数据，用于 Similar Incident Retrieval。

## 评测

```text
eval/eval_cases.json
```

离线评测用例。

```text
eval/run_eval.py
```

完整 analyze pipeline 的离线评测脚本。

```text
eval/reports/
```

评测报告输出目录，包括：

```text
eval_report.md
retrieval_benchmark_report.md
rag_ablation_report.md
eval_report_tfidf.md
eval_report_sentence-transformers.md
eval_report_hybrid.md
eval_report_chromadb.md
```

## 工具脚本

```text
scripts/build_vector_index.py
```

预构建 ChromaDB 向量索引。

```text
scripts/debug_retrieval.py
```

查看不同 retrieval mode 返回的 runbooks 和 similar incidents。

```text
scripts/rag_ablation_benchmark.py
```

RAG ablation benchmark，用来量化 TF-IDF、dense retrieval、ChromaDB、multi-query 和 metadata filter 的效果。

```text
scripts/demo_incident_analysis.py
scripts/demo_automatic_incident.py
```

命令行 Demo 脚本。

```text
scripts/clean_runtime_files.ps1
```

本地运行产物清理脚本。

## 测试

```text
tests/
```

pytest 测试，覆盖 API、analysis、RAG retrieval、LLM fallback、eval harness、demo shop 等。

## 本地运行产物

这些不是核心源码，通常不提交 Git：

```text
.venv/
runtime/
.chroma_db/
*.db
*.db-journal
*.log
__pycache__/
.pytest_cache/
```

当前项目默认把运行数据库放在：

```text
runtime/data/
```

ChromaDB 默认使用系统临时目录，也可以通过 `CHROMA_PERSIST_DIR` 指定。

## 推荐阅读顺序

如果是为了理解项目，建议按这个顺序看：

```text
README.md
DESIGN.md
docs/PROJECT_STRUCTURE.md
app/services/analysis_service.py
app/services/runbook_retriever.py
app/services/vector_store.py
eval/run_eval.py
scripts/rag_ablation_benchmark.py
```
