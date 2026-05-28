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