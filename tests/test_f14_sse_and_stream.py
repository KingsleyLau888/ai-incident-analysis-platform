"""F14 回归测试：SSE 查询限额；流式接口真实进度 + 分析不阻塞事件循环。"""

import asyncio
import json
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.api.routes as routes
from app.database import Base
from app.models import base  # noqa: F401  确保模型注册
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import incident_service, log_service, service_service


def _create_incident_with_logs(client, service_name: str, log_count: int = 1) -> dict:
    service = client.post("/services", json={"name": service_name}).json()
    for i in range(log_count):
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": f"{service_name} error {i}"},
        )
    return client.post(
        "/incidents",
        json={"service_id": service["id"], "title": f"{service_name} incident"},
    ).json()


def _in_memory_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return Session(bind=engine)


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


# ── limit 参数：默认全量不变，限额只取最新 ─────────────────────────────


def test_list_log_entries_limit_returns_latest_50():
    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="lim-svc"))
        for i in range(55):
            log_service.create_log_entry(
                db, LogEntryCreate(service_id=service.id, level="ERROR", message=f"log {i}")
            )
        latest = log_service.list_log_entries(db, limit=50)
        assert len(latest) == 50
        assert [x.id for x in latest] == list(range(6, 56))  # 最新 50 条、升序
        assert len(log_service.list_log_entries(db)) == 55  # 默认全量不变


def test_list_incidents_limit_returns_latest_50():
    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="lim-inc-svc"))
        for i in range(55):
            incident_service.create_incident(
                db, IncidentCreate(service_id=service.id, title=f"incident {i}")
            )
        latest = incident_service.list_incidents(db, limit=50)
        assert len(latest) == 50
        assert [x.id for x in latest] == list(range(6, 56))


# ── SSE 快照限额（行为保持：仍是最近 50 条，但查询在数据库侧限额） ─────────
# 注：/events 是永不结束的 SSE 流，TestClient 的同步实现会等响应跑完，
# 无法直接消费（starlette testclient 已知限制），故测试快照构建函数本身；
# 流循环的端到端行为由真实服务冒烟验证（见 docs/PROJECT_BASELINE.md F14 记录）。


def test_snapshot_builder_limits_to_latest_50():
    with _in_memory_session() as db:
        service = service_service.create_service(db, ServiceCreate(name="snap-svc"))
        for i in range(55):
            log_service.create_log_entry(
                db, LogEntryCreate(service_id=service.id, level="ERROR", message=f"error {i}")
            )
            incident_service.create_incident(
                db, IncidentCreate(service_id=service.id, title=f"incident {i}")
            )

        snapshot = routes._build_snapshot(db)

        assert len(snapshot["services"]) == 1
        assert len(snapshot["logs"]) == 50
        assert len(snapshot["incidents"]) == 50
        incident_ids = [item["id"] for item in snapshot["incidents"]]
        assert max(incident_ids) == 55 and min(incident_ids) == 6  # 恰好是最近 50 条
        log_ids = [item["id"] for item in snapshot["logs"]]
        assert max(log_ids) == 55 and min(log_ids) == 6
        assert snapshot["jobs"] == []


# ── 流式接口：真实进度 + 完成事件 + 如实标注 simulated ─────────────────


def test_stream_analyze_emits_real_progress_and_complete(client):
    incident = _create_incident_with_logs(client, "stream-svc", log_count=3)

    with client.stream("POST", f"/incidents/{incident['id']}/analyze/stream") as response:
        assert response.status_code == 200
        events = _parse_sse_events(response.iter_lines())

    progress_steps = [data["step"] for name, data in events if name == "progress"]
    # 真实流水线步骤（不再是 loading/logs/rules 假步骤）
    assert set(progress_steps) <= {
        "loading_incident", "log_filtering", "rule_detection", "planner_decision",
        "knowledge_retrieval", "summary_generation", "persistence",
    }
    assert all("elapsed_seconds" in data for name, data in events if name == "progress")

    diagnosis = [data for name, data in events if name == "diagnosis_chunk"]
    assert len(diagnosis) == 1
    assert diagnosis[0]["simulated"] is True  # 无真实 token 流，如实标注
    assert diagnosis[0]["text"]

    complete = [data for name, data in events if name == "complete"]
    assert len(complete) == 1
    assert complete[0]["analysis_id"] is not None
    assert "evidence_count" in complete[0]
    assert any(name == "trace" for name, _ in events)


def test_stream_analysis_runs_off_event_loop(client, monkeypatch):
    """分析在工作线程执行（不阻塞事件循环）的直接证据：线程 ID 不同。"""
    incident = _create_incident_with_logs(client, "stream-thread-svc", log_count=3)

    worker_thread_ids: list[int] = []
    loop_thread_ids: list[int] = []
    real_analyze = routes.analysis_service.analyze_incident
    real_put_nowait = asyncio.Queue.put_nowait

    def spy_analyze(db, incident_obj, progress_callback=None):
        worker_thread_ids.append(threading.get_ident())
        return real_analyze(db, incident_obj, progress_callback=progress_callback)

    def spy_put_nowait(queue, item):
        # 经 call_soon_threadsafe 投递，必然在事件循环线程执行
        loop_thread_ids.append(threading.get_ident())
        return real_put_nowait(queue, item)

    monkeypatch.setattr(routes.analysis_service, "analyze_incident", spy_analyze)
    monkeypatch.setattr(asyncio.Queue, "put_nowait", spy_put_nowait)

    with client.stream("POST", f"/incidents/{incident['id']}/analyze/stream") as response:
        assert response.status_code == 200
        events = _parse_sse_events(response.iter_lines())

    assert any(name == "complete" for name, _ in events)
    assert len(worker_thread_ids) == 1 and len(loop_thread_ids) >= 1
    assert worker_thread_ids[0] != loop_thread_ids[0]


def test_stream_analyze_missing_incident_returns_404(client):
    with client.stream("POST", "/incidents/999999/analyze/stream") as response:
        assert response.status_code == 404
