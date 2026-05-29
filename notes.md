# 项目理解

这个项目是一个 AI 智能运维故障分析平台。

Service：被监控的后端服务，例如 payment-service。
Log：某个服务运行时产生的日志，例如 DBConnectionTimeout。
Incident：一次线上故障，例如支付接口大量 500。

当前流程：
1. 创建 Service
2. 给 Service 导入 Logs
3. 创建 Incident
4. 后续系统会分析 Incident 关联的 Logs，判断故障类型和根因


post/incident/{incident_id}/analyze
1.根据incident_id查找对应的incident
2.根据incident的service_id查找对应的服务日志
3.rule_engine扫描日志，判断故障类型和根因
4. evidence selection 选择命中关键词的日志作为 evidence_logs。
5. summary_generation 生成摘要和建议。
6. 保存 AnalysisRun 和 Trace。
7. 返回分析结果