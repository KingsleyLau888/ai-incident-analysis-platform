"""F04：事件时间窗口与输入时区语义。

覆盖：入账统一 UTC、+08:00 与 UTC 同一时刻、计数窗口上界（未来记录不回头凑数）、
晚到日志按自身事件时间评估、边界同刻包含、极端倒序投递的已知限制、
手动事故分析窗口封顶、source 出身代替标题判断、received_at 区分送达与发生、
老库迁移（加列/回填/时间戳归一）。
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.models.service import Service
from app.schemas.log_entry import LogEntryCreate
from app.services import incident_detector, log_service
from app.services.analysis_service import _is_automatic_incident


def _in_memory_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)(), engine


def _service(db, name="f04-service"):
    service = Service(name=name)
    db.add(service)
    db.commit()
    return service


def _db_log(db, service, level, timestamp, message="boom"):
    entry = LogEntry(service_id=service.id, level=level, message=message, timestamp=timestamp)
    db.add(entry)
    db.commit()
    return entry


def _iso(value: datetime) -> str:
    return value.isoformat()


def _as_naive_utc(value: datetime) -> datetime:
    """SQLite ORM 回读会丢掉时区（本版本行为），比较前统一为 naive UTC 墙钟。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


# ── 入账归一（存储层） ─────────────────────────────────────────────────────────


def test_tz_aware_input_normalized_to_utc_at_ingestion():
    db, engine = _in_memory_session()
    try:
        service = _service(db)
        created = log_service.create_log_entry(
            db,
            LogEntryCreate(
                service_id=service.id,
                level="ERROR",
                message="payment gateway timeout",
                timestamp=datetime(2026, 9, 10, 20, 0, 0, tzinfo=timezone(timedelta(hours=8))),
            ),
        )
        # 旧行为（已复现）：ORM 丢偏移量存墙钟 20:00，当成 UTC 用 → 偏 8 小时。
        # 归一后：20:00+08:00 == 12:00 UTC，入库为 UTC 墙钟。
        assert _as_naive_utc(created.timestamp) == datetime(2026, 9, 10, 12, 0, 0)
        assert created.received_at is not None
        assert _as_naive_utc(created.received_at) >= datetime(2026, 1, 1)  # ≈ 现在
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_naive_input_treated_as_utc_at_ingestion():
    db, engine = _in_memory_session()
    try:
        service = _service(db)
        created = log_service.create_log_entry(
            db,
            LogEntryCreate(
                service_id=service.id,
                level="ERROR",
                message="naive clock",
                timestamp=datetime(2026, 9, 10, 12, 0, 0),  # 无时区 → 按 UTC 理解
            ),
        )
        assert _as_naive_utc(created.timestamp) == datetime(2026, 9, 10, 12, 0, 0)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_missing_timestamp_defaults_to_now_utc_and_received_at_is_set():
    db, engine = _in_memory_session()
    try:
        service = _service(db)
        before = datetime.now(UTC).replace(tzinfo=None)
        created = log_service.create_log_entry(
            db,
            LogEntryCreate(service_id=service.id, level="INFO", message="no clock"),
        )
        assert _as_naive_utc(created.timestamp) >= before
        assert _as_naive_utc(created.received_at) >= before
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ── 计数窗口上界 ───────────────────────────────────────────────────────────────


def test_future_timestamp_does_not_pad_earlier_burst():
    db, engine = _in_memory_session()
    try:
        service = _service(db)
        base = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        _db_log(db, service, "ERROR", base)
        second = _db_log(db, service, "ERROR", base + timedelta(seconds=10))
        far_future = _db_log(
            db, service, "ERROR", base + timedelta(days=365), message="clock skew"
        )
        # 未来记录评估自身窗口：过去两条不在其中 → 不触发
        future_decision = incident_detector.evaluate_error_burst(
            db, far_future, threshold=3, window_seconds=60
        )
        assert future_decision.should_create is False
        assert future_decision.error_count == 1
        # 第二条评估自己的窗口：未来记录不得回头凑数（旧代码这里会数出 3）
        second_decision = incident_detector.evaluate_error_burst(
            db, second, threshold=3, window_seconds=60
        )
        assert second_decision.should_create is False
        assert second_decision.error_count == 2
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_boundary_timestamp_is_inclusive_and_just_outside_is_not():
    db, engine = _in_memory_session()
    try:
        service = _service(db)
        base = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)
        _db_log(db, service, "ERROR", base)
        _db_log(db, service, "ERROR", base + timedelta(seconds=30))
        edge = _db_log(db, service, "ERROR", base + timedelta(seconds=60))
        # 边界同刻算在内：窗口 [base, base+60] 含三条
        edge_decision = incident_detector.evaluate_error_burst(
            db, edge, threshold=3, window_seconds=60
        )
        assert edge_decision.should_create is True
        assert edge_decision.error_count == 3
        # 边界外：窗口 [base+60, base+120] 只剩两条（下界同刻 base+60 仍算在内）
        outside = _db_log(db, service, "ERROR", base + timedelta(seconds=120))
        outside_decision = incident_detector.evaluate_error_burst(
            db, outside, threshold=3, window_seconds=60
        )
        assert outside_decision.should_create is False
        assert outside_decision.error_count == 2
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ── 接口层：时区同一时刻 / 乱序 / 晚到 ───────────────────────────────────────


def test_utc_and_plus8_same_instant_count_together(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "mixed-tz-service"}).json()
    base = datetime.now(UTC).replace(microsecond=0)
    beijing = timezone(timedelta(hours=8))
    stamps = [
        _iso(base),  # UTC 写法
        _iso((base + timedelta(seconds=5)).astimezone(beijing)),  # 同一时刻，+08:00 写法
        _iso(base + timedelta(seconds=10)),
    ]
    for index, stamp in enumerate(stamps):
        response = client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": f"mixed timezone failure {index}",
                "timestamp": stamp,
            },
        )
        assert response.status_code == 201
    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    # 同一时刻的两条（不同时区写法）合并计数，凑满 3 条建 1 个事故
    assert len(incidents) == 1


def test_late_arriving_log_counts_into_later_windows(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "late-log-service"}).json()
    base = datetime.now(UTC).replace(microsecond=0)
    order = [10, 20, 15, 25]  # 第 3 条晚到（事件时间在 1、2 之间），第 4 条凑满
    for index, offset in enumerate(order):
        response = client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": f"late log failure {index}",
                "timestamp": _iso(base + timedelta(seconds=offset)),
            },
        )
        assert response.status_code == 201
        if index == 2:
            # 晚到的第 3 条窗口 [T+15-60, T+15] 只含 2 条（未来记录不回头凑数）→ 不触发
            incidents = client.get(f"/incidents?service_id={service['id']}").json()
            assert incidents == []
    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    # 第 4 条窗口 [T+25-60, T+25] 含全部 4 条（含晚到的 T+15）→ 触发 1 个事故
    assert len(incidents) == 1


def test_reverse_order_delivery_does_not_trigger(client: TestClient, monkeypatch):
    """极端倒序投递不触发：已知限制，锁住当前语义（纯事件时间窗口无水印机制）。"""
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "reverse-order-service"}).json()
    base = datetime.now(UTC).replace(microsecond=0)
    for index, offset in enumerate([30, 20, 10]):
        response = client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": f"reverse order failure {index}",
                "timestamp": _iso(base + timedelta(seconds=offset)),
            },
        )
        assert response.status_code == 201
    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    assert incidents == []


# ── 分析窗口语义：手动封顶 + 出身字段 ──────────────────────────────────────────


def test_manual_incident_window_capped_at_created_at(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "manual-cap-service"}).json()
    base = datetime.now(UTC).replace(microsecond=0)
    # 事故前 30 秒的日志：属于该事故窗口
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "before incident declared",
            "timestamp": _iso(base - timedelta(seconds=30)),
        },
    )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "manual cap incident"},
    ).json()
    # 事故创建之后 60 秒的日志：封顶之后，不得混入重分析
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "after incident declared",
            "timestamp": _iso(base + timedelta(seconds=60)),
        },
    )
    client.post(f"/incidents/{incident['id']}/analyze")
    trace = client.get(f"/incidents/{incident['id']}/trace").json()
    filtering = next(step for step in trace if step["step_name"] == "log_filtering")
    assert filtering["detail"] == "Selected 1 logs for service."


def test_source_field_replaces_title_detection(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "source-field-service"}).json()
    # 标题伪装成自动事故，但出身由服务端定：人工创建 = manual
    manual = client.post(
        "/incidents",
        json={
            "service_id": service["id"],
            "title": "Automatic alert for source-field-service",
        },
    ).json()
    assert manual["source"] == "manual"
    # 自动爆发创建的事故出身 = automatic
    for index in range(3):
        client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": f"auth token failure {index}",
            },
        )
    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    automatic = [item for item in incidents if item["source"] == "automatic"]
    assert len(automatic) == 1
    assert _is_automatic_incident(
        Incident(service_id=service["id"], title="Automatic alert for x", source=None)
    ) is False  # 老数据 source 缺失按 manual 语义，标题不再参与判断


def test_received_at_distinguishes_arrival_from_event_time(client: TestClient):
    service = client.post("/services", json={"name": "arrival-service"}).json()
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "old event delivered now",
            "timestamp": "2020-01-01T00:00:00+00:00",
        },
    )
    logs = client.get(f"/logs?service_id={service['id']}").json()
    event_time = datetime.fromisoformat(logs[0]["timestamp"])
    received_at = datetime.fromisoformat(logs[0]["received_at"])
    assert event_time.year == 2020
    assert received_at.year >= 2026  # 送达时间 ≈ 现在，与事件时间（2020）区分开


# ── 同服务连续两场不同事故（边界回归） ────────────────────────────────────────


def test_consecutive_bursts_create_two_incidents(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "consecutive-service"}).json()
    # 时间戳用服务器默认（按送达顺序）：事故创建时刻夹在两场爆发之间，
    # 第二场爆发从上一事故创建时刻起算，不再回头数第一场的日志（F03/F04 语义）
    db_messages = [
        "DBConnectionTimeout while connecting to shop-primary",
        "shop-primary database unavailable during checkout",
        "Checkout API returned 500 after database write failure",
    ]
    for message in db_messages:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    auth_messages = [
        "Unauthorized checkout token rejected by auth middleware",
        "Authentication failed while creating checkout session",
        "Checkout API returned 401 after invalid customer token",
    ]
    for message in auth_messages:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    assert len(incidents) == 2
    assert {item["source"] for item in incidents} == {"automatic"}
    analyses = [
        client.get(f"/incidents/{item['id']}/analysis").json() for item in incidents
    ]
    assert {analysis["issue_type"] for analysis in analyses} == {
        "database_issue",
        "auth_issue",
    }


# ── 老库迁移 ─────────────────────────────────────────────────────────────────


def test_migration_adds_received_at_and_normalizes_timestamps(tmp_path):
    from app.database_migrations import ensure_log_time_columns

    engine = create_engine(f"sqlite:///{tmp_path / 'old_logs.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE log_entries ("
                "id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, "
                "level VARCHAR(30) DEFAULT 'INFO', message TEXT, timestamp DATETIME)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO log_entries (id, service_id, level, message, timestamp) VALUES "
                "(1, 1, 'ERROR', 'naive', '2026-09-10 12:00:00.000000'),"
                "(2, 1, 'ERROR', 'plus8', '2026-09-10 12:00:00.000000+08:00'),"
                "(3, 1, 'ERROR', 'utc', '2026-09-10 04:00:00.000000+00:00'),"
                "(4, 1, 'INFO', 'none', NULL)"
            )
        )
    summary = ensure_log_time_columns(engine)
    assert summary == {"added_column": 1, "normalized": 2, "unchanged": 1, "unparseable": 0}
    with engine.begin() as connection:
        received_at = connection.execute(
            text("SELECT received_at FROM log_entries WHERE id = 1")
        ).scalar()
        assert received_at == "2026-09-10 12:00:00.000000"  # 回填自 timestamp（已归一）
        rows = connection.execute(
            text("SELECT timestamp FROM log_entries ORDER BY id")
        ).fetchall()
    stored = [row[0] for row in rows]
    # 无时区 → 不变（按 UTC 理解）；+08:00 → 换算 UTC；带偏移 UTC → 去偏移统一文本
    assert stored == [
        "2026-09-10 12:00:00.000000",
        "2026-09-10 04:00:00.000000",
        "2026-09-10 04:00:00.000000",
        None,
    ]


def test_migration_adds_incident_source_and_backfills_by_title(tmp_path):
    from app.database_migrations import ensure_incident_source_column

    engine = create_engine(f"sqlite:///{tmp_path / 'old_incidents.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE incidents ("
                "id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, "
                "title VARCHAR(200), status VARCHAR(30), created_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO incidents (id, service_id, title, status) VALUES "
                "(1, 1, 'Automatic alert for payment-service', 'open'),"
                "(2, 1, 'manual incident', 'open')"
            )
        )
    summary = ensure_incident_source_column(engine)
    assert summary == {"added_column": 1}
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT id, source FROM incidents ORDER BY id")
        ).fetchall()
    assert rows == [(1, "automatic"), (2, "manual")]
    # 幂等：再跑一遍不加列不报错
    assert ensure_incident_source_column(engine) == {"added_column": 0}
