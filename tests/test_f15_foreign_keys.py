"""F15 收尾：SQLite 外键检查启用与孤儿体检。

验收：应用引擎每连接开启 PRAGMA foreign_keys；引用不存在父行的写入被数据库拒绝；
`scan_foreign_key_orphans` 对各类外键报数准确、对缺失表安全。
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.analysis_job import AnalysisJob
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.models.service import Service


def _fk_engine():
    """与 app.database 相同配置的临时引擎：建表 + 打开外键检查。"""
    from app.database import enable_sqlite_foreign_keys

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(bind=engine)
    return engine


def test_app_engine_enforces_foreign_keys():
    from app.database import engine as app_engine

    # 应用引擎的每个连接都应已打开外键检查（PRAGMA 是每连接生效的）
    with app_engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_fk_engine_enforces_foreign_keys():
    engine = _fk_engine()
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        engine.dispose()


def test_orphan_log_insert_is_rejected():
    engine = _fk_engine()
    db = sessionmaker(bind=engine)()
    try:
        with pytest.raises(IntegrityError):
            db.add(LogEntry(service_id=999, level="ERROR", message="orphan log"))
            db.commit()
        db.rollback()
        # 父行存在则正常写入（约束只挡孤儿，不挡合法数据）
        service = Service(name="fk-service")
        db.add(service)
        db.commit()
        db.add(LogEntry(service_id=service.id, level="ERROR", message="valid log"))
        db.commit()
    finally:
        db.close()
        engine.dispose()


def test_orphan_incident_and_job_insert_are_rejected():
    engine = _fk_engine()
    db = sessionmaker(bind=engine)()
    try:
        with pytest.raises(IntegrityError):
            db.add(Incident(service_id=999, title="orphan incident"))
            db.commit()
        db.rollback()
        service = Service(name="fk-inc-service")
        db.add(service)
        db.commit()
        # 事故引用了不存在的服务会被拒；任务引用不存在的事故也会被拒
        with pytest.raises(IntegrityError):
            db.add(AnalysisJob(incident_id=999, trigger="manual"))
            db.commit()
    finally:
        db.close()
        engine.dispose()


def test_scan_reports_orphans_accurately():
    from app.database_migrations import scan_foreign_key_orphans

    engine = _fk_engine()
    db = sessionmaker(bind=engine)()
    try:
        service = Service(name="scan-service")
        db.add(service)
        db.commit()
        # 合法行：服务、日志、事故、分析任务（analysis_run_id 为 NULL 不查父行）
        db.add(LogEntry(service_id=service.id, level="ERROR", message="ok"))
        incident = Incident(service_id=service.id, title="ok incident")
        db.add(incident)
        db.commit()
        db.add(AnalysisJob(incident_id=incident.id, trigger="manual"))
        db.commit()
        assert scan_foreign_key_orphans(engine) == {
            "log_entries_without_service": 0,
            "incidents_without_service": 0,
            "analysis_runs_without_incident": 0,
            "analysis_jobs_without_incident": 0,
            "analysis_jobs_without_run": 0,
            "analysis_traces_without_run": 0,
            "incident_evidence_without_run": 0,
            "incident_evidence_without_log": 0,
            "feedback_without_run": 0,
        }
    finally:
        db.close()
        engine.dispose()


def test_scan_finds_orphans_in_old_data():
    from app.database_migrations import scan_foreign_key_orphans

    # 模拟旧库（不开外键约束）里已有的孤儿行：体检应能数出来
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO log_entries (id, service_id, level, message, timestamp) "
                "VALUES (1, 999, 'ERROR', 'orphan', '2026-09-10 12:00:00.000000')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO incidents (id, service_id, title, status, created_at) "
                "VALUES (1, 998, 'orphan incident', 'open', '2026-09-10 12:00:00.000000')"
            )
        )
    try:
        result = scan_foreign_key_orphans(engine)
        assert result["log_entries_without_service"] == 1
        assert result["incidents_without_service"] == 1
        assert result["analysis_jobs_without_incident"] == 0
    finally:
        engine.dispose()


def test_scan_is_safe_on_empty_database():
    from app.database_migrations import scan_foreign_key_orphans

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        # 完全空库：没有任何表，体检应安静返回空结果而不是报错
        assert scan_foreign_key_orphans(engine) == {}
    finally:
        engine.dispose()
