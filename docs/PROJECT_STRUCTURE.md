# 项目结构说明

这个项目分成两类文件：源码/配置，以及本地运行产物。

## 核心源码

```text
app/
```

AI Incident Copilot 后端主程序。

```text
app/api/
```

FastAPI 路由，比如日志接收、incident 创建、analyze、dashboard、SSE。

```text
app/services/
```

核心业务逻辑，包括日志保存、自动 incident detection、analysis pipeline、retrieval、eval 辅助等。

```text
app/agent/
```

Agent 相关逻辑，包括自动选择 pipeline/agent 的 router、ReAct Agent、工具定义。

```text
app/llm/
```

LLM client 层，包括 Mock LLM、OpenAI-compatible client、fallback factory。

```text
app/rule_engine/
```

规则检测逻辑，根据日志关键词识别 `database_issue`、`timeout_issue`、`auth_issue` 等。

```text
app/models/
```

数据库表模型，也就是 SQLAlchemy models。

```text
app/schemas/
```

API 请求和响应结构，也就是 Pydantic schemas。

## Demo 和集成

```text
demo_shop_system/
```

模拟被监控的电商 checkout 系统。用户在这里下单，系统产生日志并发送到 AI Incident Copilot。

```text
demo_payment_service/
```

早期 payment service demo。

```text
integrations/
```

日志接入示例，比如 Python logging handler、Fluent Bit 配置。

```text
templates/
```

Dashboard 页面模板。

## RAG / 知识库数据

```text
runbooks/
```

故障处理文档，用于 runbook retrieval。

```text
data/
```

模拟历史事故数据，用于 similar incident retrieval。

```text
eval/
```

离线评测用例、评测脚本、评测报告。

## 工具与测试

```text
scripts/
```

演示脚本、retrieval 对比脚本、清理脚本。

```text
tests/
```

pytest 测试。

## 文档

```text
README.md
DESIGN.md
docs/
```

项目介绍、架构设计和补充说明。

## 本地运行产物

这些不是源码，通常可以清理：

```text
*.log
*.db-journal
auto_demo.db
sqlite_probe.db
.demo_runtime/
__pycache__/
.pytest_cache/
```

这些要看情况：

```text
runtime/data/incident-live.db
runtime/data/app.db
runtime/data/demo_shop.db
.chroma_db/
```

`runtime/data/incident-live.db` / `runtime/data/app.db` 存 AI Incident 平台数据。删掉后 services、logs、incidents、analysis、trace 会清空。

`runtime/data/demo_shop.db` 存 Demo Shop 的商品和订单数据。删掉后 demo shop 会重新初始化。

`.chroma_db/` 是 ChromaDB 本地向量库。删掉后如果启用 `RETRIEVAL_MODE=chromadb`，下次会重新建索引。
