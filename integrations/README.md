# 日志接入

## Python 应用

```python
import logging
from integrations.python_logging_handler import IncidentPlatformHandler

logger = logging.getLogger("payment-service")
logger.addHandler(
    IncidentPlatformHandler(
        platform_url="http://127.0.0.1:8000",
        service_name="payment-service",
    )
)
```

应用继续正常调用 `logger.info()`、`logger.error()`，Handler 会自动注册服务并上传日志。

## 通用 HTTP 接入

```http
POST /ingest/logs
Content-Type: application/json

{
  "service_name": "payment-service",
  "level": "ERROR",
  "message": "DBConnectionTimeout while connecting to mysql-primary"
}
```

## Fluent Bit

`fluent-bit.conf` 展示了从日志文件读取并发送到 `/ingest/logs` 的基本配置。实际使用时需要根据原始日志格式配置 parser，把 `message` 和 `level` 映射为平台字段。
