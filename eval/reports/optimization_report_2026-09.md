# Runbook 检索优化报告（2026-09）

> 本轮从 2026-09-08 审计基线出发，重做了一轮干净、可复现的检索优化。
> 旧简历数字（59.09%→95.45%）经复现失败已作废，本文所有数字均为本轮
> 在同环境、同评测集、可验证有效后端（effective_mode）下重新测得。

## 一、结论摘要

| 指标 | 基线（09-08 审计） | 本轮后 | 变化 |
|---|---|---|---|
| 27 例全集 Runbook Top-1（TF-IDF） | 55.56% | **88.89%** | +33.33 |
| 27 例全集 Runbook Recall（TF-IDF） | 77.16% | **84.57%** | +7.41 |
| 27 例全集 Runbook P@3（TF-IDF） | 60.49% | **74.07%** | +13.58 |
| 27 例失败案例数 | 11 | **9** | −2 |
| 22 例消融 tfidf 单查询 Top-1 | 86.36% | **100.00%** | +13.64 |
| 22 例消融 chromadb 多查询+元数据过滤 Top-1 | 81.82% | 81.82% | 持平（复现） |
| 27 例 4 后端对比最高 Top-1 | tfidf 88.89% | **hybrid 92.59%** | — |

F11 门槛对照：Top-1 ≥75% **达标**（88.89%）；Recall ≥85% **差 0.43 未达**（84.57%），
缺口与根因见第五节。

## 二、改动清单（4 个杠杆）

| # | 文件 | 改动 | 数据裁决 |
|---|---|---|---|
| 1 | app/services/runbook_chunker.py | `infer_issue_type` 顺序优先 → 类别关键词命中次数计分，平票按类别表顺序 | **保留**（Top-1 +3.7，P@3 +7.4；12 本手册全文件一致标注） |
| 2 | app/services/runbook_retriever.py | 新增 `RUNBOOK_FILTER_MODE` hard/soft/off + 降权系数；查询构建去重/截断/可读类型词 | **保留 hard 为默认**（off 灾难、soft 负收益）；查询构建**保留**（Top-1 +29.6 的最大来源） |
| 3 | app/services/query_rewriter.py | 变体 1 追加证据摘录；`_extract_keywords` 重写（小写证据词可被提取）+ 停用词表 | **保留**（证据词进入查询是核心杠杆） |
| 4 | app/services/analysis_service.py | 证据去重；PIPELINE_VARIANT_TOP_K（默认 5）、RRF_K（默认 60）可调 | **默认值不变**（top_k=8 负收益；k∈{20,60,150} 无差异） |

新增测试：tests/test_runbook_chunker.py 9 项（标注修复回归）。全套 71 passed。

## 三、关键发现

1. **标注修复**（杠杆 1）："identity provider" 的 "provider" 曾把 token 签名轮换手册的
   chunk 误标为 timeout，污染超时案例候选池；cache_stampede 手册 6/10 chunk 误标 database。
   计分制后 38 个 chunk 改标、31 个朝正确方向收敛。
2. **查询构建是最大杠杆**（杠杆 3）：旧管道路径的模板变体几乎不带证据词（关键词提取只认
   大写开头词，全小写证据整体丢弃），TF-IDF 检索在"半盲"状态下运行。变体 1 追加证据摘录后
   Top-1 +29.6。
3. **融合参数不敏感**（杠杆 4）：RRF k 在 20/60/150 三档完全无差异；每变体 top_k 5→8
   净负收益（修复不了目标案例，反伤 2 个已过案例）。
4. **旧 95.45% 无法复现**：22 例消融 chromadb 配置在新环境实测 81.82%（与 dense 一致），
   旧数字不可信；现版本所有消融配置的 effective_mode 与请求后端一致（真实生效）。
5. **hybrid 后端在全集上最优**：92.59%（稀疏+稠密 RRF 融合），代价是 ~2.2s 延迟；
   chromadb 81.48% / 169ms 是低延迟最优解。

## 四、评测证据

- 27 例正式轮：eval/reports/eval_report.md（tfidf，pipeline，Judge 关闭）
- 4 后端对比：eval/reports/retrieval_benchmark_report.md（tfidf/dense/hybrid/chromadb）
- 22 例消融：eval/reports/rag_ablation_report.md（5 配置，effective_mode 列逐一核对）
- 过程证据：runtime/audit/ 下 step1/step2/step3-step4 证据文件 + 各轮 eval 报告 + 消融基线

评测环境：LLM_PROVIDER=mock、CROSS_ENCODER_ENABLED=0、HF_HUB_OFFLINE=1、
TRANSFORMERS_OFFLINE=1、ANALYSIS_MODE=pipeline；评测集 eval/eval_cases.json 未做任何改动；
runbooks/ 语料未增删；无按 case_id 硬编码。

## 五、剩余失败与根因（9 例）

范围外（4）：2 例规则误报（cache/memory 警告被误判为事故）、2 例证据选择失败
（检索结果已正确）。检索失败 5 例：

| 案例 | 根因 |
|---|---|
| rag-config-secret-database / rag-redis-secret-cache | 硬过滤结构性排除：database/cache 案例需要 auth 标注的 config_secret_mismatch.md；soft 模式整体负收益（IDF 在全量语料上重拟合改变同类型内排序），不可兼得 |
| rag-network-policy-postgres | postgres_primary_unavailable 在单一变体排第 5，RRF 单列表分数（0.0154）拼不过 firewall 多列表累积（0.0486） |
| rag-queue-lag-not-db | 证据关键词被 "timed/out/waiting" 等废词占满槽位；message_queue_lag 单列表分数天花板 |
| rag-dns-provider-timeout | 稀疏词面重叠无法桥接 "provider timed out" → "api degradation"（需语义检索） |

## 六、可写进简历的表述（供参考）

> 重构 AI 事故分析平台的 Runbook 检索链路：修复 chunk 类型标注的误标（计分制替代顺序优先）、
> 让证据日志真正进入检索查询（关键词提取重写 + 证据摘录变体）、对过滤策略与融合参数做全配置
> 消融实验。离线评测（27 例）Runbook Top-1 55.56%→88.89%、Recall 77.16%→84.57%；
> 22 例消融中 TF-IDF 单查询 Top-1 达 100%；4 后端对比（TF-IDF/dense/ChromaDB/hybrid）
> hybrid 达 92.59%，所有配置的 effective_mode 与请求后端一致（真实生效可复现）。
