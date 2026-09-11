from contextlib import asynccontextmanager

from fastapi import FastAPI

# F17（2026-09-11 复核 R01）：.env 必须最先加载——app.database 在导入时读取
# DATABASE_URL 并创建 engine，embedding_service 在导入时固定重排开关；晚于这些
# 导入调用 prepare_config() 时，配置看似生效、实际早已按默认值固定。
from app.config import prepare_config

prepare_config()

from app.api.routes import pages_router, router
from app.database import Base, engine
from app.database_migrations import (
    ensure_active_job_unique_index,
    ensure_analysis_result_columns,
    ensure_incident_dedupe_columns,
    ensure_incident_source_column,
    ensure_log_time_columns,
)
from app.middleware import apply_request_protection
from app.models import base
from app.services import analysis_job_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 开机清场（F02）：进程中断遗留的 running 标失败、pending 重新执行
    summary = analysis_job_service.recover_interrupted_jobs(engine)
    if summary["failed"] or summary["requeued"]:
        print(f"[F02 recovery] interrupted jobs at startup: {summary}", flush=True)
    yield


def create_app() -> FastAPI:
    # 配置加载与校验已在模块级完成（见文件顶部 F17 注释），此处直接建表/迁移
    Base.metadata.create_all(bind=engine)
    ensure_analysis_result_columns(engine)
    ensure_incident_dedupe_columns(engine)
    ensure_active_job_unique_index(engine)
    ensure_log_time_columns(engine)
    ensure_incident_source_column(engine)

    app = FastAPI(
        title="AI-Powered Incident Analysis Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    # 请求保护（F16）：大小上限 + 写入频率限流（环境变量可调，默认宽松）
    apply_request_protection(app)
    # R04：页面壳无锁（浏览器需先拿到页面输入钥匙），数据/写入接口带锁
    app.include_router(pages_router)
    app.include_router(router)
    return app


app = create_app()
