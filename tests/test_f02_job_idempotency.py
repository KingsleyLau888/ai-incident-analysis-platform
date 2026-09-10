"""F02 回归测试：任务幂等领取、成功重入不重跑、进行中不重复、启动恢复、防连点去重。"""

import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import router
from app.database import Base, get_db
from app.models import base  # noqa: F401  确保模型注册
from app.models.analysis import AnalysisRun
from app.models.analysis_job import AnalysisJob
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import analysis_job_service, incident_service, log_service, service_service


@pytest.fixture
def job_engine(tmp_path):
    """文件型 SQLite：每个线程独立连接，能真实并发领取（内存单连接池测不了抢号）。"""
    engine = create_engine(
        f"sqlite:///{tmp_path.as_posix()}/f02.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


def _make_incident_with_logs(db: Session, name: str) -> Incident:
    service = service_service.create_service(db, ServiceCreate(name=name))
    for i in range(3):
        log_service.create_log_entry(
            db, LogEntryCreate(service_id=service.id, level="ERROR", message=f"{name} error {i}")
        )
    return incident_service.create_incident(
        db, IncidentCreate(service_id=service.id, title=f"{name} incident")
    )


def _analysis_run_count(engine) -> int:
    with Session(bind=engine) as db:
        return db.scalar(select(func.count(AnalysisRun.id))) or 0


# ── 原子领取：并发执行同 job 只有一个赢家 ──────────────────────────────


def test_run_job_concurrent_claims_only_one_winner(job_engine):
    with Session(bind=job_engine) as db:
        incident = _make_incident_with_logs(db, "claim-svc")
        job = analysis_job_service.create_job(db, incident.id, trigger="automatic")
        job_id = job.id

    threads = [
        threading.Thread(target=analysis_job_service.run_job, args=(job_engine, job_id))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
        assert not thread.is_alive()

    assert _analysis_run_count(job_engine) == 1  # 并发执行同 job 最多一个有效结果
    with Session(bind=job_engine) as db:
        job = db.get(AnalysisJob, job_id)
        assert job.status == "succeeded"
        assert job.analysis_run_id is not None


# ── 成功任务重入：直接复用已有结果，不重跑 ─────────────────────────────


def test_run_job_rerun_on_succeeded_is_noop(job_engine):
    with Session(bind=job_engine) as db:
        incident = _make_incident_with_logs(db, "rerun-svc")
        job = analysis_job_service.create_job(db, incident.id, trigger="manual")
        job_id = job.id

    analysis_job_service.run_job(job_engine, job_id)
    analysis_job_service.run_job(job_engine, job_id)  # 重入：不应再产生结果

    assert _analysis_run_count(job_engine) == 1
    with Session(bind=job_engine) as db:
        job = db.get(AnalysisJob, job_id)
        assert job.status == "succeeded"


def test_run_job_on_running_job_is_noop(job_engine):
    with Session(bind=job_engine) as db:
        incident = _make_incident_with_logs(db, "running-svc")
        job = analysis_job_service.create_job(db, incident.id, trigger="manual")
        job.status = "running"
        db.commit()
        job_id = job.id

    analysis_job_service.run_job(job_engine, job_id)  # 已被别的执行者领取：no-op

    assert _analysis_run_count(job_engine) == 0
    with Session(bind=job_engine) as db:
        job = db.get(AnalysisJob, job_id)
        assert job.status == "running"
        assert job.analysis_run_id is None


# ── 初始进度提交异常：记 failed，不卡 running ──────────────────────────


def test_run_job_initial_progress_failure_marks_failed(job_engine, monkeypatch):
    with Session(bind=job_engine) as db:
        incident = _make_incident_with_logs(db, "flaky-svc")
        job = analysis_job_service.create_job(db, incident.id, trigger="manual")
        job_id = job.id

    calls = {"n": 0}
    real_set_progress = analysis_job_service._set_progress

    def flaky_set_progress(db, job, step, detail):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("progress write exploded")
        return real_set_progress(db, job, step, detail)

    monkeypatch.setattr(analysis_job_service, "_set_progress", flaky_set_progress)

    analysis_job_service.run_job(job_engine, job_id)

    with Session(bind=job_engine) as db:
        job = db.get(AnalysisJob, job_id)
        assert job.status == "failed"
        assert "progress write exploded" in job.error


# ── 开机清场：running 明确失败，pending 重新执行 ──────────────────────


def test_recover_interrupted_jobs_requeues_pending_and_fails_running(job_engine):
    with Session(bind=job_engine) as db:
        incident = _make_incident_with_logs(db, "recover-svc")

        pending = analysis_job_service.create_job(db, incident.id, trigger="automatic")
        pending_id = pending.id

        # running 任务放在独立事故上：每事故最多一个未完成任务（F03 唯一索引）
        other_incident = _make_incident_with_logs(db, "recover-running-svc")
        running = AnalysisJob(
            incident_id=other_incident.id, trigger="automatic", status="running"
        )
        db.add(running)
        db.flush()
        running_id = running.id
        db.commit()

    summary = analysis_job_service.recover_interrupted_jobs(job_engine)
    assert summary == {"failed": 1, "requeued": 1}

    deadline = time.time() + 30
    while time.time() < deadline:
        with Session(bind=job_engine) as db:
            pending = db.get(AnalysisJob, pending_id)
            if pending.status in {"succeeded", "failed"}:
                break
        time.sleep(0.1)

    with Session(bind=job_engine) as db:
        pending = db.get(AnalysisJob, pending_id)
        assert pending.status == "succeeded"  # 排队中的任务开机后被接着跑完
        assert pending.analysis_run_id is not None

        running = db.get(AnalysisJob, running_id)
        assert running.status == "failed"  # 中断的进行中任务被明确标失败
        assert "Interrupted by process shutdown" in running.error


# ── 接口防连点：未完成任务复用，完成后允许新任务 ───────────────────────


@pytest.fixture
def api_with_db(tmp_path):
    """独立于 conftest client 的测试应用：暴露 Session 工厂以便预置排队任务。"""
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
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_incident_with_logs_via(client, session_factory, name: str) -> dict:
    service = client.post("/services", json={"name": name}).json()
    incident = client.post(
        "/incidents", json={"service_id": service["id"], "title": f"{name} incident"}
    ).json()
    # 服务层直写日志：不触发自动事故检测，只为分析提供上下文
    with session_factory() as db:
        for i in range(3):
            log_service.create_log_entry(
                db,
                LogEntryCreate(service_id=service["id"], level="ERROR", message=f"{name} error {i}"),
            )
    return incident


def test_analysis_job_endpoint_reuses_active_job(api_with_db):
    client, session_factory = api_with_db
    incident = _create_incident_with_logs_via(client, session_factory, "dedupe-svc")

    with session_factory() as db:
        existing = analysis_job_service.create_job(db, incident["id"], trigger="manual")
        existing_id = existing.id  # 预置一个排队中的任务

    response = client.post(f"/incidents/{incident['id']}/analysis-jobs")
    assert response.status_code == 202
    assert response.json()["id"] == existing_id  # 复用原任务，不新开

    jobs = client.get(f"/analysis-jobs?incident_id={incident['id']}").json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == existing_id
    assert jobs[0]["status"] == "succeeded"  # 补发执行把排队任务跑完了


def test_analysis_job_endpoint_creates_new_job_after_success(api_with_db):
    client, session_factory = api_with_db
    incident = _create_incident_with_logs_via(client, session_factory, "reanalyze-svc")

    first = client.post(f"/incidents/{incident['id']}/analysis-jobs").json()
    second = client.post(f"/incidents/{incident['id']}/analysis-jobs").json()

    assert second["id"] != first["id"]  # 完成后再次触发 = 有意重分析，允许新任务
    jobs = client.get(f"/analysis-jobs?incident_id={incident['id']}").json()
    assert len(jobs) == 2
    assert all(job["status"] == "succeeded" for job in jobs)
