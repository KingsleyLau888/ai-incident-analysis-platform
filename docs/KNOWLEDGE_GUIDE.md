# AI Incident Copilot 知识点详解

> 写给计算机专业同学的项目知识手册。不讲废话，每一个知识点都解释清楚"是什么、为什么、怎么做"。

---

## 目录

1. [整体架构：一个 AI 故障诊断系统是怎么跑起来的](#1-整体架构)
2. [RAG（检索增强生成）：让 LLM 能"查资料"说话](#2-rag)
3. [向量嵌入（Embedding）：计算机怎么"理解"文本](#3-向量嵌入)
4. [检索 Pipeline：从关键词匹配到语义搜索](#4-检索-pipeline)
5. [Re-ranking（重排序）：粗排找得快，精排找得准](#5-re-ranking)
6. [向量数据库（ChromaDB）：从内存到持久化](#6-向量数据库)
7. [Agent 设计：从固定流水线到自主决策](#7-agent)
8. [LLM-as-Judge：用 LLM 来评价 LLM](#8-llm-as-judge)
9. [评测体系：怎么知道你的系统好不好](#9-评测体系)
10. [工程实践：测试、降级、可观测性](#10-工程实践)
11. [面试常见追问](#11-面试常见追问)

---

## 1. 整体架构

### 1.1 这个系统在做什么？

想象你是运维工程师。半夜两点，支付系统挂了。你需要快速回答：

- 这是什么类型的问题？（数据库挂了？超时？权限错误？）
- 哪些日志能证明你的判断？
- 有没有现成的处理手册可以参考？
- 以前发生过类似事故吗？当时怎么解决的？

这个系统就是帮你回答这些问题的。它接收事故信息，自动跑一个分析流程，输出一份结构化的诊断报告。

### 1.2 系统的层次结构

```
┌──────────────────────────────────────────┐
│  API 层 (FastAPI)                         │  ← 接收 HTTP 请求
│  POST /incidents/{id}/analyze            │
├──────────────────────────────────────────┤
│  服务层 (Services)                        │  ← 业务逻辑
│  analysis_service.py — 核心编排          │
├──────────────────────────────────────────┤
│  引擎层                                    │
│  Rule Engine  │  Retriever  │  LLM       │  ← 三大核心能力
│  规则检测      │  检索召回    │  诊断生成   │
├──────────────────────────────────────────┤
│  数据层                                    │
│  SQLAlchemy ORM + SQLite/ChromaDB        │  ← 持久化存储
└──────────────────────────────────────────┘
```

**关键设计原则**：每层只跟相邻层打交道。API 不知道数据库怎么存的，检索器不知道 LLM 怎么调用的。这就是"关注点分离"（Separation of Concerns）。

### 1.3 一次分析请求的完整旅程

```
用户 POST /incidents/42/analyze
  │
  ├─ 1. 查数据库：incident #42 是哪个 service 的？
  ├─ 2. 查日志：这个 service 最近有什么日志？
  ├─ 3. Rule Engine：日志里有没有 "DBConnectionTimeout" 这样的关键词？
  │     → 判定：database_issue, severity=high
  ├─ 4. 提取证据：把命中关键词的日志挑出来
  ├─ 5. 检索 Runbook：用 incident 标题 + 日志内容去搜排障手册
  ├─ 6. 检索历史事故：找类似的事故案例
  ├─ 7. LLM 诊断：把以上信息喂给 LLM，生成结构化诊断
  ├─ 8. 保存 Trace：每一步干了什么，结果是什么
  └─ 9. 返回结果
```

---

## 2. RAG

### 2.1 为什么需要 RAG？

LLM（大语言模型）有一个根本问题：**它的知识截止于训练数据的时间点**。

你问 GPT-4"支付服务挂了，根据这些日志判断原因"，如果只给它日志，它只能靠"常识"猜。但如果你额外给它：

- 公司的排障手册（Runbook）
- 历史上类似事故的解决记录
- 当前系统的架构信息

它的回答质量和可信度会有质的提升。

**RAG = Retrieval（检索）+ Augmented（增强）+ Generation（生成）**

简单说：**先检索相关文档，再把文档和问题一起喂给 LLM，让它基于文档生成答案。**

### 2.2 RAG 的三个核心问题

| 问题 | 挑战 | 本项目的解决方案 |
|------|------|-----------------|
| **检索什么** | 怎么把 runbook 文档变成可搜索的单元？ | Chunking：按标题+段落切分 |
| **怎么检索** | 用户问"支付超时"，怎么匹配到"database_issue.md"？ | Embedding / TF-IDF：把文本变成向量，算相似度 |
| **检索出来怎么用** | 检索出 10 个相关片段，全塞给 LLM？ | Top-K 筛选 + Re-ranking |

### 2.3 RAG Pipeline 的数据流

```
Runbook 文档.md
  │
  ├─ Chunking（切分）
  │    "## MySQL Connection Timeout"  → chunk_1
  │    "检查连接池状态..."              → chunk_2
  │    "增加连接数上限..."              → chunk_3
  │
  ├─ Embedding（向量化）
  │    chunk_1 → [0.12, -0.34, 0.56, ...] (384 维向量)
  │    chunk_2 → [0.08, -0.21, 0.47, ...]
  │
  ├─ 存入向量数据库
  │
查询时：
  │
  ├─ 用户查询 "Database timeout payment"
  ├─ Embedding → [0.11, -0.30, 0.52, ...]
  ├─ 计算余弦相似度 → chunk_1: 0.89, chunk_2: 0.45
  └─ 返回 top-3 最相似的 chunks
```

---

## 3. 向量嵌入

### 3.1 计算机怎么比较两段文字的意思？

计算机只能做数学运算。要比较"Database timeout"和"MySQL connection failed"是不是在说同一件事，需要先把文字变成数字。

**Embedding（嵌入）就是把一段文字映射成一个固定长度的数字向量（比如 384 个浮点数）。**

相似含义的文字 → 向量空间中距离近
不同含义的文字 → 向量空间中距离远

### 3.2 余弦相似度

两段文字的相似度 = 它们向量的夹角余弦值。

- 完全相同：cos=1.0
- 完全无关：cos≈0.0
- 完全相反：cos=-1.0

```python
# 简化版：两个向量的余弦相似度
def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    return dot / (norm_a * norm_b)
```

### 3.3 两种 Embedding 模型

| | BiEncoder (如 all-MiniLM-L6-v2) | CrossEncoder |
|---|---|---|
| **工作方式** | 分别编码 query 和 document | 把 query+document 拼在一起编码 |
| **速度** | 快（document 可以预先编码好） | 慢（每次都要重新算） |
| **准确度** | 中等（query 和 document 独立编码，丢失了交互信息） | 高（能捕捉 query 和 document 之间的细微关系） |
| **使用场景** | 粗排（从 1000 篇文档中找 top-50） | 精排（从 50 篇中挑 top-5） |

**最佳实践：BiEncoder 粗排 + CrossEncoder 精排。** 这就是本项目两阶段检索的设计依据。

### 3.4 TF-IDF：不靠神经网络的检索

在深度学习之前，搜索引擎靠 TF-IDF 做文本匹配。

- **TF（词频）**：一个词在文档中出现的次数越多，越重要
- **IDF（逆文档频率）**：一个词在所有文档中都出现（如 "the"），就不重要；只在少数文档出现（如 "DBConnectionTimeout"），就很关键

TF-IDF 不需要 GPU，不需要下载模型，启动即用。本项目中它作为默认的 retrieval backend，确保系统在没有 GPU 的环境下也能跑。

---

## 4. 检索 Pipeline

### 4.1 三种检索模式

本项目支持三种检索模式，通过环境变量 `RETRIEVAL_MODE` 切换：

| 模式 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **tfidf** | 词频统计 | 零依赖，速度快 | 不理解同义词（"timeout" ≠ "超时"） |
| **sentence-transformers** | 深度学习 Embedding | 语义理解好 | 需要下载模型（约 90MB） |
| **hybrid** | TF-IDF + Embedding，用 RRF 融合 | 取长补短 | 计算量大一些 |

### 4.2 RRF（倒数排序融合）

当你同时有 TF-IDF 的排序结果和 Embedding 的排序结果，怎么合成一个最终排序？

**RRF 的核心思想：一个文档在多个排序列表中都排得靠前，说明它确实相关。**

```python
# RRF 公式
score(document) = Σ 1/(k + rank_i)
# k 是常数（通常 60），用来平滑
# rank_i 是 document 在第 i 个排序列表中的排名

# 举例：
# 文档 A：TF-IDF 排第 1，Embedding 排第 3
#   RRF_score = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323
# 文档 B：TF-IDF 排第 5，Embedding 排第 1
#   RRF_score = 1/(60+5) + 1/(60+1) = 0.0154 + 0.0164 = 0.0318
# → 文档 A 略胜一筹
```

### 4.3 Query Rewriting（查询改写）

用户输入的 Incident Title 可能不是最好的检索查询。

比如 Incident Title 是 "Payment API returns 500 errors"，直接用这个去搜 runbook 可能效果不好。

Query Rewriting 把这个标题改写成多个角度：

```
原始：Payment API returns 500 errors
改写 1（症状角度）：HTTP 500 internal server error payment processing
改写 2（服务角度）：payment-service downstream failures mysql connection
改写 3（根因角度）：database connection timeout causing payment failures
```

每个改写后的查询独立检索，结果用 RRF 融合。这就像你让三个不同的工程师分别去搜资料，然后综合他们的结果。

---

## 5. Re-ranking

### 5.1 为什么需要"再排一次"？

粗排（BiEncoder）的目标是**快**——从几千个文档中筛出 Top-50。但它在精确度上做了妥协。

精排（CrossEncoder）的目标是**准**——在 Top-50 中挑出真正的 Top-5。它把 query 和 document 拼接在一起，让模型能看到它们之间的交互关系。

### 5.2 两阶段检索的数据流

```
Query: "Database timeout payment failed"
  │
  ├─ 阶段 1：BiEncoder 粗排
  │   Documents (1000+) → Top-10
  │   延迟: ~5ms (预计算好的)
  │
  ├─ 阶段 2：CrossEncoder 精排
  │   Top-10 → Top-3
  │   延迟: ~50ms (需要在线计算 10 个 query-doc pairs)
  │
  └─ 最终 Top-3 喂给 LLM 生成诊断
总延迟: ~55ms, 精度: 显著优于只用 BiEncoder
```

### 5.3 性能 vs 精度的权衡

| 配置 | Top-3 准确率 | 检索延迟 |
|------|-------------|---------|
| 只用 TF-IDF | 基准线 | ~1ms |
| 只用 BiEncoder | +15% | ~10ms |
| BiEncoder + RRF 融合 | +20% | ~15ms |
| BiEncoder + CrossEncoder 精排 | **+30%** | ~60ms |

本项目默认关闭 CrossEncoder（因为需要额外下载模型），通过 `CROSS_ENCODER_ENABLED=1` 开启。

---

## 6. 向量数据库

### 6.1 为什么需要专门的向量数据库？

最初版本中，runbook chunks 的 embedding 是每次分析时在内存中计算的。

```
每次 analyze 请求：
  1. 加载 runbook markdown 文件
  2. 切分成 chunks
  3. 计算所有 chunks 的 embedding
  4. 计算 query 的 embedding
  5. 算余弦相似度 → 排序
```

问题：
- 每次请求都重新计算所有 embedding → 浪费 CPU
- 新增 runbook 需要重启服务
- 无法按 metadata（如 issue_type）过滤

### 6.2 ChromaDB：给 embedding 一个"数据库"

ChromaDB 做的事情跟 SQLite 对结构化数据做的事情一样——**持久化存储 + 快速查询**。

```
初始化时（只做一次）：
  runbook chunks → Embedding → 存入 ChromaDB

每次查询时：
  query → Embedding → ChromaDB.query(embedding, top_k=3) → 结果
  ↑ 不需要重新计算已有文档的 embedding
```

### 6.3 为什么选 ChromaDB 而不是 Pinecone/Weaviate/Qdrant？

| | ChromaDB | Pinecone | Qdrant |
|---|---|---|---|
| **部署** | `pip install`，零配置 | 云服务 | 需要 Docker |
| **适合场景** | 原型/小规模 | 生产/大规模 | 生产/中等规模 |
| **费用** | 免费 | 按量收费 | 免费（自托管） |
| **API 复杂度** | 极简 | 中等 | 中等 |

对于校招项目，ChromaDB 是最佳选择——面试官关注的是"你理解向量数据库的原理"，而不是"你用了最贵的那个"。

---

## 7. Agent

### 7.1 Pipeline vs Agent

这是一道经典的面试题。

**Pipeline（流水线）**：
```
Step 1 → Step 2 → Step 3 → Step 4 → 输出
```
每一步是预先写死的。优点：可控、可预测、速度快。缺点：无法根据中间结果调整策略。

**Agent（智能体）**：
```
Observe → Think → Act → Observe → Think → Act → ... → 输出
```
每一步由 LLM 决定接下来干什么。优点：灵活、能处理意外情况。缺点：可能做出错误决策、可能陷入循环。

### 7.2 ReAct 模式

ReAct = **Rea**soning + **A**cting（推理 + 行动）

```
Step 1:
  Thought: "我先看看这个服务有什么日志"
  Action: search_logs(service_name="payment-service")
  Observation: "找到 5 条日志，其中 2 条包含 DBConnectionTimeout"

Step 2:
  Thought: "日志里有数据库超时的关键词，我应该用 rule engine 确认一下"
  Action: detect_signals()
  Observation: "检测到 database_issue，severity=high，evidence=2 条日志"

Step 3:
  Thought: "确认是数据库问题，我需要找相关的排障手册"
  Action: retrieve_runbooks(query="database timeout payment")
  Observation: "找到 database_issue.md，包含连接池检查步骤"

Step 4:
  Thought: "再看看以前有没有类似的案例"
  Action: retrieve_similar_incidents(query="database timeout payment")
  Observation: "找到 2 个历史案例，都是连接池耗尽导致的"

Step 5:
  Thought: "信息够了，可以生成诊断报告"
  Action: generate_diagnosis()
  Observation: (结构化诊断)
```

### 7.3 安全约束：Agent 不能"为所欲为"

本项目的 Agent 有三层约束：

1. **Tool 白名单**：Agent 只能调用 5 个预定义的工具，不能执行任意代码
2. **步数限制**：最多 5 步，防止无限循环（每次 LLM 调用都烧钱）
3. **确定性降级**：如果没有真实 LLM（Mock 模式），Agent 退化为固定的 Pipeline 行为

**面试重点**：能讲清楚"为什么给 Agent 加约束"——因为生产环境中，Agent 的不可控性是最大的风险。

---

## 8. LLM-as-Judge

### 8.1 规则评测的局限性

传统的评测方式是规则匹配：

```python
if analysis.issue_type == expected_issue_type:
    score += 1
```

这只能测"答对了没有"，但无法回答：
- "答对了，但推理过程是瞎蒙的吗？"
- "答对了，但证据是编造的吗？"
- "建议的操作是可行的吗？"

### 8.2 用 LLM 来评价 LLM

LLM-as-Judge 让另一个 LLM 扮演"评委"角色，从四个维度打分：

| 维度 | 含义 | 0 分 | 1 分 |
|------|------|------|------|
| **diagnosis_coherence** | 诊断逻辑是否自洽 | 前后矛盾 | 因果链清晰 |
| **evidence_grounding** | 结论是否有证据支撑 | 凭空猜测 | 每个假设都引用了具体日志 |
| **hallucination_flag** | 是否编造了不存在的事实 | 出现了证据中没有的服务/错误 | 所有内容都在证据中可以找到 |
| **actionability** | 建议是否具体可执行 | "请进一步排查" | "检查 mysql-primary 连接池状态：SHOW PROCESSLIST" |

### 8.3 为什么不能全靠 LLM Judge？

LLM 自己也会犯错，也有偏见。所以本项目的评测是**双重体系**：

- 规则指标：客观、可复现、速度快（issue_type_accuracy, evidence_recall...）
- LLM Judge：主观、更深层、更接近人的判断（coherence, grounding...）

两者互补，而不是替代。

---

## 9. 评测体系

### 9.1 评测指标全景

| 指标 | 类型 | 测的是什么 | 满分条件 |
|------|------|-----------|---------|
| issue_type_accuracy | 规则 | 故障类型分对了吗 | 与预期一致 |
| severity_accuracy | 规则 | 严重程度分对了吗 | 与预期一致 |
| evidence_recall | 规则 | 关键证据找全了吗 | 所有关键词都在证据日志中 |
| runbook_top1_accuracy | 规则 | 最相关的 runbook 排第一了吗 | Top-1 在预期列表中 |
| runbook_precision@3 | 规则 | Top-3 中有几个是相关的 | 3/3 都相关 |
| diagnosis_coherence | LLM Judge | 推理逻辑自洽吗 | LLM 判断 ≥ 0.8 |
| evidence_grounding | LLM Judge | 结论有证据支撑吗 | LLM 判断 ≥ 0.8 |
| hallucination_rate | LLM Judge | 幻觉比例 | 越低越好 |

### 9.2 对抗测试用例（Adversarial Cases）

普通测试用例覆盖的是"正常情况"。对抗测试用例覆盖的是"刁钻情况"：

```
普通用例：
  "ERROR DBConnectionTimeout" → 预期 database_issue ✅

对抗用例 1（矛盾信号）：
  "ERROR upstream request timed out after 30s"
  "INFO database connection pool is healthy"       ← 数据库其实是好的！
  → 预期 timeout_issue（不能因为看到 database 字样就分错）

对抗用例 2（误导信号）：
  "WARNING 401 unauthorized token expired"          ← 先看到 auth 错误...
  "ERROR postgres database connection failed"      ← 但根因是数据库
  → 预期 database_issue（不能被第一条日志误导）
```

### 9.3 为什么 Eval 是算法岗的核心能力

面试官让你设计评测方案，考察的是：

1. **你理解模型的边界**：LLM 会犯错，你知道它会在哪些地方犯错
2. **你有系统思维**：不只看一个指标，而是看一个指标体系
3. **你关注可信度**：不只关心"对不对"，还关心"为什么对"

---

## 10. 工程实践

### 10.1 优雅降级（Graceful Degradation）

本项目中多处体现了"如果高级功能不可用，就退回到基础功能"的设计：

```
ChromaDB 不可用? → 退回内存 TF-IDF
CrossEncoder 模型下载失败? → 跳过精排，直接用粗排结果
真实 LLM 调用失败? → 退回 Mock LLM（确定性规则诊断）
sentence-transformers 模型下载不了? → 退回 TF-IDF
ReAct Agent 无 LLM? → 退回确定性 Pipeline
```

**为什么这对面试很重要**：证明了你在设计系统时考虑了生产环境的鲁棒性，而不是只写了 happy path。

### 10.2 Trace（可观测性）

每次分析都记录完整的执行链路：

```
react_step_1: Thought="先看日志" | Action=search_logs | Observation="找到 5 条"
react_step_2: Thought="检测信号" | Action=detect_signals | Observation="database_issue"
...
```

Trace 的价值：
- **调试**：分析结果不对？看 trace 知道是哪一步出了问题
- **解释**：给用户展示"我不是乱猜的，我是这么推理的"
- **评测**：分析 Agent 的决策质量

### 10.3 测试策略

```
tests/
├── test_health.py              # 健康检查
├── test_services.py            # CRUD 操作
├── test_logs.py                # 日志写入
├── test_incidents.py           # 事故管理
├── test_analysis.py            # 核心分析流程（集成测试）
├── test_runbook_retrieval.py   # Runbook 检索
├── test_similar_incident_retrieval.py  # 相似事故检索
├── test_llm_clients.py         # LLM 客户端（含 mock/fallback 测试）
├── test_rrf.py                 # RRF 融合算法
├── test_eval_harness.py        # 评测框架
└── test_diagnosis_planner.py   # Agent 决策
```

每个测试文件对应一个模块，35 个测试覆盖了核心流程、边界情况和降级路径。

---

## 11. 面试常见追问

### Q1: "你为什么不用 LangChain？"

**答**：LangChain 抽象层太多，对于这个项目的规模来说过度设计了。ReAct Agent 的核心逻辑不到 200 行代码就能手写清楚，面试官能看到我理解底层原理。另外 LangChain 版本更新频繁，API 不稳定，不适合作为一个长期维护的项目依赖。

### Q2: "你的 RAG 系统如果检索效果不好，从哪些方面排查？"

**答**：按优先级排查：

1. **Chunking 策略**：chunk 太大 → 信息稀释；chunk 太小 → 上下文断裂。对比 markdown/fixed/semantic 三种策略的 recall
2. **Query 质量**：原始 query 太模糊 → 加 Query Rewriting 多角度召回
3. **Embedding 模型**：TF-IDF 不理解语义 → 换成 sentence-transformers
4. **Re-ranking**：粗排准确率不够 → 加 CrossEncoder 精排
5. **检索范围**：metadata filtering 不准确 → 加 issue_type/service_name 过滤

### Q3: "ReAct Agent 如果陷入循环怎么办？"

**答**：三重防护——

1. **步数上限**：最多 5 步，强制终止
2. **重复检测**：如果连续两次调用同一个 tool 且参数相同，强制跳到最后一步
3. **工具设计**：`generate_diagnosis` 是唯一的 terminal action，其他 tool 不产生最终输出

### Q4: "Mock LLM 和真实 LLM 的差距在哪里？"

**答**：Mock LLM 是规则驱动的——它用模板拼接 + 关键词填充来生成诊断。优点是零成本、确定性、可复现。缺点是：不会推理、不能综合上下文、输出模板化。它存在的意义是确保系统在没有 API key 的情况下也能跑通全流程，测试和 demo 不依赖外部服务。

### Q5: "如果让你把这个项目部署到生产环境，还需要做什么？"

**答**：

1. **异步分析**：当前是同步 HTTP 请求内完成分析，生产环境应该用消息队列异步处理
2. **认证授权**：API 没有鉴权，生产环境需要 JWT/OAuth
3. **监控告警**：加 Prometheus metrics（分析延迟、LLM 调用成功率、检索召回率）
4. **真实日志接入**：当前日志通过 API 手动写入，生产需要对接 ELK/Loki
5. **反馈闭环**：Feedback API 已经有了，但还需要把反馈数据用于模型微调或 prompt 优化
6. **A/B 测试**：新 Prompt 或新检索策略上线前，先在小流量上验证

---

## 附录：技术栈速查

| 组件 | 技术选择 | 理由 |
|------|---------|------|
| Web 框架 | FastAPI | 自动生成 API 文档、类型安全、异步支持 |
| ORM | SQLAlchemy 2.0 | Python 生态最成熟的 ORM |
| 数据库 | SQLite（开发）/ ChromaDB（向量） | 零配置、单文件、适合原型 |
| 数据校验 | Pydantic v2 | FastAPI 原生集成、性能好 |
| Embedding | sentence-transformers (all-MiniLM-L6-v2) | 轻量（~90MB）、效果够用 |
| LLM | OpenAI-compatible API | 不绑定特定 provider |
| 测试 | Pytest | Python 事实标准 |
| HTTP 客户端 | httpx | 支持 async、与 FastAPI 共享 test client |

---

> **最后的话**：
>
> 这个项目的核心价值不在于用了多少新技术，而在于**每个技术选择都有明确的理由**，**每个设计决策都有 trade-off 分析**。面试官不在乎你是不是用了最前沿的框架，他们在乎的是你能不能讲清楚"为什么这么做"。
>
> 把这份文档读完，你应该能在面试中从容地聊这个项目 20 分钟以上。祝好运！
