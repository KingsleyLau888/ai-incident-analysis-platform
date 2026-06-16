from fastapi import FastAPI

from app.api.routes import router
from app.database import Base, engine
from app.database_migrations import ensure_analysis_result_columns
from app.models import base


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_analysis_result_columns(engine)

    app = FastAPI(
        title="AI-Powered Incident Analysis Platform",
        version="0.1.0",
    )
    app.include_router(router)
    return app


app = create_app()
