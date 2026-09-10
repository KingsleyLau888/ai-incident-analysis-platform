from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.database import Base, engine
from app.config import prepare_config
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
    # F17：启动即校验配置（.env 加载 + 非法取值报错，不静默回退）
    prepare_config()
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
    app.include_router(router)
    return app


app = create_app()
