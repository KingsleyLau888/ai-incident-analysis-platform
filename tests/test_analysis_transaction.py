"""F01 回归测试：分析结果、证据、Trace 必须原子提交。

进度回调内部会 commit（见 analysis_job_service._set_progress）。"persistence"
进度若在提交前发出，会把半成品 AnalysisRun 提前提交，之后写入失败时
rollback 无法撤回。测试用文件库 + 第二连接观察中间状态，并注入 Trace
写入故障验证失败后无可见半成品。
"""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import base  # noqa: F401  确保模型注册
from app.models.analysis import AnalysisRun, AnalysisTrace, IncidentEvidence
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import (
    analysis_job_service,
    analysis_service,
    incident_service,
    log_service,
    service_service,
)


def _setup_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'txn.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_database_incident(session):
    service = service_service.create_service(
        session, ServiceCreate(name="txn-payment-service")
    )
    for message in [
        "DBConnectionTimeout while connecting to postgres",
        "Order creation failed because database is unavailable",
        "Checkout API returned 500 after database write failure",
    ]:
        log_service.create_log_entry(
            session,
            LogEntryCreate(service_id=service.id, level="ERROR", message=message),
        )
    return incident_service.create_incident(
        session,
        IncidentCreate(
            service_id=service.id,
            title="Checkout failing after database errors",
            description="checkout errors",
        ),
    )


def _committing_callback(db: object, steps: list[str], on_step=None):
    """模拟 run_job 的进度回调：记录步骤并 commit（这是半成品的毒源）。"""

    def callback(step: str, detail: str) -> None:
        steps.append(step)
        if on_step is not None:
            on_step(step, detail)
        db.commit()

    return callback


def test_progress_never_exposes_half_product(tmp_path):
    engine, session_factory = _setup_engine(tmp_path)
    steps: list[str] = []
    observations: dict[str, tuple[int, int, int]] = {}

    def observe(label: str) -> None:
        # 第二连接偷看：(AnalysisRun 数, 证据行数, Trace 行数)
        with session_factory() as other:
            observations[label] = (
                other.scalar(select(func.count()).select_from(AnalysisRun)),
                other.scalar(select(func.count()).select_from(IncidentEvidence)),
                other.scalar(select(func.count()).select_from(AnalysisTrace)),
            )

    with session_factory() as db:
        incident = _create_database_incident(db)

        def on_step(step, _detail):
            if step == "summary_generation":  # 提交前最后一个进度点
                observe("before_persistence")
            elif step == "persistence":
                observe("at_persistence")

        callback = _committing_callback(db, steps, on_step)
        analysis = analysis_service.analyze_incident(db, incident, progress_callback=callback)

    assert "persistence" in steps
    # 提交前：其他连接看不到任何分析结果（无半成品泄漏）
    assert observations["before_persistence"] == (0, 0, 0)
    # persistence 进度点：结果已整体提交、三样齐全
    # （旧代码在此刻能看到 1 个结果但证据/Trace 为 0 —— 半成品）
    runs, evidence, traces = observations["at_persistence"]
    assert (runs, evidence >= 1, traces >= 1) == (1, True, True)
    assert analysis.id is not None
    with session_factory() as other:
        assert other.scalar(select(func.count()).select_from(AnalysisRun)) == 1


def test_trace_failure_rollback_leaves_no_half_product(tmp_path, monkeypatch):
    engine, session_factory = _setup_engine(tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("trace persist failed")

    monkeypatch.setattr(analysis_service, "_persist_pipeline_trace", _boom)

    with session_factory() as db:
        incident = _create_database_incident(db)
        callback = _committing_callback(db, [])

        with pytest.raises(RuntimeError):
            analysis_service.analyze_incident(db, incident, progress_callback=callback)
        db.rollback()

    # 回滚后不得残留半成品 AnalysisRun（旧代码会残留 1 个：被进度回调提前提交）
    with session_factory() as other:
        assert other.scalar(select(func.count()).select_from(AnalysisRun)) == 0


def test_run_job_trace_failure_marks_failed_without_half_product(tmp_path, monkeypatch):
    engine, session_factory = _setup_engine(tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError("trace persist failed")

    monkeypatch.setattr(analysis_service, "_persist_pipeline_trace", _boom)

    with session_factory() as db:
        incident = _create_database_incident(db)
        job = analysis_job_service.create_job(db, incident.id, trigger="manual")
        job_id = job.id

    analysis_job_service.run_job(engine, job_id)

    with session_factory() as db:
        job = analysis_job_service.get_job(db, job_id)
        assert job.status == "failed"
        assert "trace persist failed" in job.error
        # 任务失败可追踪，且没有任何可见的分析结果（无论半成品还是成品）
        assert db.scalar(select(func.count()).select_from(AnalysisRun)) == 0
