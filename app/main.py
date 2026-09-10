from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.database import Base, engine
from app.database_migrations import ensure_analysis_result_columns
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
    Base.metadata.create_all(bind=engine)
    ensure_analysis_result_columns(engine)

    app = FastAPI(
        title="AI-Powered Incident Analysis Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
