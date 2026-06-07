import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.database import Base, get_db
from app.models import base
from app.services.embedding_service import get_sentence_transformer_embedder


@pytest.fixture(autouse=True)
def isolate_retrieval_environment(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("RUNBOOK_EMBEDDING_BACKEND", raising=False)
    get_sentence_transformer_embedder.cache_clear()
    yield
    get_sentence_transformer_embedder.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
