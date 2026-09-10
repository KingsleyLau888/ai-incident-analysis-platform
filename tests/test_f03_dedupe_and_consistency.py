"""F03 回归测试：去重不依赖分析结果、事故任务原子提交、并发单建、
活动任务唯一约束、手动分析建任务、流式失败事件、服务重名稳定返回。"""

import json
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.routes as routes
from app.database import Base, get_db
from app.models import base  # noqa: F401  确保模型注册
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import (
    analysis_job_service,
    automatic_incident_service,
    incident_service,
    log_service,
    service_service,
)


def _in_memory_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine)


def _db_error_log(db, service_id: int, message: str):
    return log_service.create_log_entry(
        db, LogEntryCreate(service_id=service_id, level="ERROR", message=message)
    )


# ── 去重不依赖分析结果：任务未执行时同类日志复用事故 ───────────────────


def test_same_type_logs_reuse_incident_while_job_pending(monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    monkeypatch.setenv("AUTO_INCIDENT_DEDUPE_MINUTES", "10")

    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="seq-svc"))
        incident = None
        for i in range(3):
            log = _db_error_log(db, service.id, f"DBConnectionTimeout attempt {i}")
            incident, job_id = automatic_incident_service.process_log_entry(db, log)
        assert incident is not None and job_id is not None
        assert incident.inferred_issue_type is not None  # 创建时保存初步类型

        # 任务仍 pending（服务层不自动执行）。窗口从事故创建时间起重新计数，
        # 再攒满 3 条同类日志后触发"再建"判断：应复用原事故，而不是新开
        existing, new_job_id = None, None
        for i in range(3, 6):
            log = _db_error_log(db, service.id, f"DBConnectionTimeout attempt {i}")
            existing, new_job_id = automatic_incident_service.process_log_entry(db, log)
        assert new_job_id is None
        assert existing is not None and existing.id == incident.id

        assert len(incident_service.list_incidents(db, service_id=service.id)) == 1


def test_different_issue_type_creates_separate_incident(monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    monkeypatch.setenv("AUTO_INCIDENT_DEDUPE_MINUTES", "10")

    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="split-svc"))
        for i in range(3):
            log = _db_error_log(db, service.id, f"DBConnectionTimeout while connecting {i}")
            automatic_incident_service.process_log_entry(db, log)
        for i in range(3):
            log = _db_error_log(db, service.id, f"Unauthorized token rejected {i}")
            automatic_incident_service.process_log_entry(db, log)

        incidents = incident_service.list_incidents(db, service_id=service.id)
        assert len(incidents) == 2  # 不同故障不误合并
        assert {item.inferred_issue_type for item in incidents} == {
            "database_issue",
            "auth_issue",
        }


# ── 事故与任务一次提交：中途失败不留孤儿 ───────────────────────────────


def test_incident_and_job_creation_is_atomic(monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")

    class ExplodingJob:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("job insert exploded")

    monkeypatch.setattr(automatic_incident_service, "AnalysisJob", ExplodingJob)

    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="atomic-svc"))
        for i in range(2):
            log = _db_error_log(db, service.id, f"DBConnectionTimeout attempt {i}")
            automatic_incident_service.process_log_entry(db, log)
        log3 = _db_error_log(db, service.id, "DBConnectionTimeout attempt 3")
        with pytest.raises(RuntimeError):
            automatic_incident_service.process_log_entry(db, log3)

        db.rollback()  # 请求层等价：会话关闭即回滚
        assert incident_service.list_incidents(db, service_id=service.id) == []
        assert analysis_job_service.list_jobs(db, incident_id=None) == []


# ── 并发日志：同爆发只建一个事故 ───────────────────────────────────────


def test_concurrent_logs_create_single_incident(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "2")
    engine = create_engine(
        f"sqlite:///{tmp_path.as_posix()}/f03.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as db:
        service = service_service.create_service(db, ServiceCreate(name="race-svc"))
        service_id = service.id
        log1 = _db_error_log(db, service_id, "DBConnectionTimeout attempt 1")
        automatic_incident_service.process_log_entry(db, log1)  # 1 < 2，不触发

    errors: list[Exception] = []
    start = threading.Barrier(2)  # 同时放行，最大化并发窗口

    def worker(i: int) -> None:
        try:
            start.wait()
            with Session(bind=engine) as db:
                log = _db_error_log(db, service_id, f"DBConnectionTimeout attempt {i}")
                automatic_incident_service.process_log_entry(db, log)
        except Exception as exc:  # pragma: no cover - 收集并发异常用于断言
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in (2, 3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert not errors
    with Session(bind=engine) as db:
        incidents = incident_service.list_incidents(db, service_id=service_id)
        assert len(incidents) == 1
        jobs = analysis_job_service.list_jobs(db, incident_id=incidents[0].id)
        assert len(jobs) == 1
        assert incidents[0].inferred_issue_type is not None


# ── 活动任务唯一约束：每事故最多一个 pending/running ───────────────────


def test_active_job_unique_index_blocks_second_active_job():
    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="idx-svc"))
        incident = incident_service.create_incident(
            db, IncidentCreate(service_id=service.id, title="idx incident")
        )
        first = analysis_job_service.create_job(db, incident.id)  # pending

        with pytest.raises(IntegrityError):
            analysis_job_service.create_job(db, incident.id)  # 第二个活动任务被索引拒绝
        db.rollback()

        # 完成后不拦：有意重分析允许新建任务
        first.status = "succeeded"
        db.commit()
        second = analysis_job_service.create_job(db, incident.id)
        assert second.id != first.id


# ── 接口层：并发先查后建竞态由唯一索引兜底 ─────────────────────────────


@pytest.fixture
def api_with_db(tmp_path):
    """独立于 conftest client 的测试应用：暴露 Session 工厂以便预置任务。"""
    engine = create_engine(
        f"sqlite:///{tmp_path.as_posix()}/api.db",
        connect_args={"check_same_thread": False},
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
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_analysis_job_endpoint_recovers_after_race(api_with_db, monkeypatch):
    client, session_factory = api_with_db
    service = client.post("/services", json={"name": "race-api-svc"}).json()
    incident = client.post(
        "/incidents", json={"service_id": service["id"], "title": "race incident"}
    ).json()

    with session_factory() as db:
        existing = analysis_job_service.create_job(db, incident["id"], trigger="manual")
        existing_id = existing.id

    # 模拟并发窗口：预检查没看到已有任务，直接撞唯一约束
    real_find = analysis_job_service.find_active_job
    calls = {"n": 0}

    def race_window(db, incident_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real_find(db, incident_id)

    monkeypatch.setattr(analysis_job_service, "find_active_job", race_window)

    response = client.post(f"/incidents/{incident['id']}/analysis-jobs")
    assert response.status_code == 202
    assert response.json()["id"] == existing_id  # 唯一索引兜底后取到已有任务

    jobs = client.get(f"/analysis-jobs?incident_id={incident['id']}").json()
    assert len(jobs) == 1


# ── 手动分析也建任务（F13 遗留收尾）────────────────────────────────────


def _create_incident_with_logs(client, service_name: str) -> dict:
    service = client.post("/services", json={"name": service_name}).json()
    # 1 ERROR + 2 INFO：不触发自动检测（阈值 3），但给分析留上下文
    client.post(
        "/logs",
        json={"service_id": service["id"], "level": "ERROR", "message": f"{service_name} failed"},
    )
    for i in range(2):
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "INFO", "message": f"{service_name} info {i}"},
        )
    return client.post(
        "/incidents", json={"service_id": service["id"], "title": f"{service_name} incident"}
    ).json()


def test_manual_analyze_creates_job(client):
    incident = _create_incident_with_logs(client, "manual-job-svc")

    response = client.post(f"/incidents/{incident['id']}/analyze")
    assert response.status_code == 201
    analysis_id = response.json()["id"]

    jobs = client.get(f"/analysis-jobs?incident_id={incident['id']}").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["analysis_run_id"] == analysis_id
    assert jobs[0]["trigger"] == "manual"


def _parse_sse_events(lines) -> list[tuple[str, dict]]:
    events = []
    event_name, data = None, None
    for line in lines:
        if line.startswith("event: "):
            event_name = line[len("event: "):]
        elif line.startswith("data: "):
            data = json.loads(line[len("data: "):])
        elif line == "" and event_name is not None:
            events.append((event_name, data))
            event_name, data = None, None
    return events


def test_stream_analyze_failure_marks_job_failed_and_emits_error(client, monkeypatch):
    incident = _create_incident_with_logs(client, "stream-fail-svc")

    def boom(db, incident_obj, progress_callback=None):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(routes.analysis_service, "analyze_incident", boom)

    with client.stream("POST", f"/incidents/{incident['id']}/analyze/stream") as response:
        events = _parse_sse_events(response.iter_lines())

    assert any(name == "error" for name, _ in events)  # 如实发错误事件，不半路断流
    assert not any(name == "complete" for name, _ in events)

    jobs = client.get(f"/analysis-jobs?incident_id={incident['id']}").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"
    assert "model exploded" in jobs[0]["error"]


# ── 同名服务：明确 409 或归到已有服务，不再 500 ────────────────────────


def test_create_service_duplicate_name_returns_409(client):
    client.post("/services", json={"name": "dup-svc"})
    response = client.post("/services", json={"name": "dup-svc"})
    assert response.status_code == 409


def test_ingest_name_conflict_returns_existing_service(client, monkeypatch):
    existing = client.post("/services", json={"name": "ext-svc"}).json()

    def explode_create(db, service_in):
        raise IntegrityError("INSERT INTO services", {}, Exception("duplicate name"))

    real_list = routes.service_service.list_services
    calls = {"n": 0}

    def race_list(db):
        calls["n"] += 1
        if calls["n"] == 1:
            return []  # 模拟并发窗口：预查没看到已有服务
        return real_list(db)

    monkeypatch.setattr(routes.service_service, "list_services", race_list)
    monkeypatch.setattr(routes.service_service, "create_service", explode_create)

    response = client.post(
        "/ingest/logs",
        json={"service_name": "ext-svc", "level": "INFO", "message": "hello"},
    )
    assert response.status_code == 201

    services = client.get("/services").json()
    matching = [item for item in services if item["name"] == "ext-svc"]
    assert len(matching) == 1  # 归到已有服务，不重复注册
    assert matching[0]["id"] == existing["id"]

    logs = client.get(f"/logs?service_id={existing['id']}").json()
    assert logs[-1]["message"] == "hello"
