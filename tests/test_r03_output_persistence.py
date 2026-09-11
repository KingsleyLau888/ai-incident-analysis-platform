"""R03（2026-09-11 复核）：诊断输出端到端保留。

覆盖：
- AnalysisRun 新三栏（missing_information / investigation_notes /
  final_evidence_log_ids）模型往返与旧库迁移；
- pipeline 模式：模型声明的缺失信息落库，重新查库仍可读；API 序列化输出；
- Agent 模式：关键词命中的额外日志进入最终证据（[E#] 编号映射持久化，
  证据行带 "Agent keyword search match." 出身），调查笔记（[N#]）落库。
"""

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.database_migrations import ensure_analysis_result_columns
from app.models import base  # noqa: F401  确保模型注册
from app.models.analysis import AnalysisRun
from app.llm.base import DiagnosisResult, RootCauseHypothesis, StructuredDiagnosis
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import (
    analysis_service,
    incident_service,
    log_service,
    service_service,
)


class FakeLLMClient:
    """pipeline 诊断替身：返回带 missing_information 的结构化诊断。"""

    def diagnose(self, **kwargs) -> DiagnosisResult:
        return DiagnosisResult(
            diagnosis=StructuredDiagnosis(
                diagnosis_summary="fake summary",
                root_cause_hypotheses=[
                    RootCauseHypothesis(
                        cause="cause",
                        confidence=0.8,
                        supporting_evidence=["[E1] log line"],
                    )
                ],
                impact_scope="svc",
                structured_suggested_actions=["check"],
                missing_information=["Need database pool metrics"],
            ),
            provider="fake",
        )


def _setup_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'r03.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_database_incident(session):
    service = service_service.create_service(
        session, ServiceCreate(name="r03-payment-service")
    )
    for message in [
        "DBConnectionTimeout while connecting to mysql-primary",
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


# ── 模型往返 ──────────────────────────────────────────────────────────

def test_analysis_run_roundtrips_new_fields(tmp_path):
    engine, session_factory = _setup_engine(tmp_path)
    with session_factory() as db:
        run = AnalysisRun(
            incident_id=1,
            issue_type="database_issue",
            severity="high",
            root_cause_summary="s",
            suggested_actions="a",
        )
        run.set_structured_diagnosis(
            diagnosis_summary="sum",
            root_cause_hypotheses=[{"cause": "c", "confidence": 0.5,
                                    "supporting_evidence": ["[E1] log"]}],
            impact_scope="svc",
            structured_suggested_actions=["check"],
            missing_information=["Need pool metrics"],
        )
        run.set_investigation_context(
            investigation_notes=["Timeline built with 3 of 3 logs."],
            final_evidence_log_ids=[11, 12, 13],
        )
        db.add(run)
        db.commit()
        run_id = run.id

    with session_factory() as db:
        reloaded = db.get(AnalysisRun, run_id)
        assert reloaded.missing_information == ["Need pool metrics"]
        assert reloaded.investigation_notes == ["Timeline built with 3 of 3 logs."]
        assert reloaded.final_evidence_log_ids == [11, 12, 13]


# ── 旧库迁移 ──────────────────────────────────────────────────────────

def test_migration_adds_new_columns_to_old_database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'old.db'}",
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        # 模拟旧库：analysis_runs 只有老列，没有 R03 三栏
        connection.execute(text(
            "CREATE TABLE analysis_runs (id INTEGER PRIMARY KEY, "
            "incident_id INTEGER, issue_type VARCHAR(80))"
        ))
    ensure_analysis_result_columns(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("analysis_runs")}
    for name in ("missing_information", "investigation_notes", "final_evidence_log_ids"):
        assert name in columns


# ── pipeline 模式：落库 + 重新查库 + API 序列化 ────────────────────────

def test_pipeline_persists_missing_information_and_evidence_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(analysis_service, "get_llm_client", FakeLLMClient)
    engine, session_factory = _setup_engine(tmp_path)

    with session_factory() as db:
        incident = _create_database_incident(db)
        run = analysis_service.analyze_incident(db, incident)
        assert run.missing_information == ["Need database pool metrics"]
        assert run.investigation_notes == []  # pipeline 无调查笔记
        assert len(run.final_evidence_log_ids) == 3  # 规则证据的 [E#] 映射
        expected_ids = list(run.final_evidence_log_ids)
        run_id = run.id
        db.commit()

    with session_factory() as db:
        # 重载后按编号还原材料：E1 就是第一条规则证据日志
        reloaded = db.get(AnalysisRun, run_id)
        assert reloaded.missing_information == ["Need database pool metrics"]
        assert reloaded.final_evidence_log_ids == expected_ids
        assert reloaded.final_evidence_log_ids[0] == expected_ids[0]


def test_api_serializes_new_fields(client, monkeypatch):
    monkeypatch.setattr(analysis_service, "get_llm_client", FakeLLMClient)

    service = client.post("/services", json={"name": "r03-api-service"}).json()
    for message in [
        "DBConnectionTimeout while connecting to mysql-primary",
        "Order creation failed because database is unavailable",
        "Checkout API returned 500 after database write failure",
    ]:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Checkout failing"},
    ).json()

    response = client.post(f"/incidents/{incident['id']}/analyze")
    assert response.status_code == 201
    analysis = response.json()
    assert analysis["missing_information"] == ["Need database pool metrics"]
    assert analysis["investigation_notes"] == []
    assert len(analysis["final_evidence_log_ids"]) == 3

    # 从 API 重新读取（重载路径）同样保留
    reloaded = client.get(f"/incidents/{incident['id']}/analysis").json()
    assert reloaded["missing_information"] == ["Need database pool metrics"]
    assert reloaded["final_evidence_log_ids"] == analysis["final_evidence_log_ids"]


# ── Agent 模式：关键词命中的额外日志进入最终证据并持久化 ──────────────

class _KeywordSearchAgentLLM:
    """驱动：search_logs → detect_signals → query_logs_by_keyword →
    generate_diagnosis。关键词命中一条规则证据之外的日志。"""

    def __init__(self) -> None:
        self.calls = 0

    def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
        self.calls += 1
        actions = [
            {"thought": "Collect logs.", "action": "search_logs",
             "action_input": {"service_name": "r03-agent-service"}},
            {"thought": "Classify signals.", "action": "detect_signals",
             "action_input": {}},
            {"thought": "Search for inventory errors.", "action": "query_logs_by_keyword",
             "action_input": {"keyword": "inventory"}},
            {"thought": "Enough evidence.", "action": "generate_diagnosis",
             "action_input": {}},
        ]
        return actions[min(self.calls - 1, len(actions) - 1)]


def test_agent_extra_keyword_logs_persisted_with_provenance(client, monkeypatch):
    monkeypatch.setenv("REACT_AGENT_ENABLED", "1")
    monkeypatch.setattr(
        analysis_service, "_get_react_llm_client", _KeywordSearchAgentLLM
    )

    service = client.post("/services", json={"name": "r03-agent-service"}).json()
    # 规则证据日志（database_issue）+ 一条不含规则关键词的 ERROR 日志
    for message in [
        "DBConnectionTimeout while connecting to mysql-primary",
        "ERROR inventory reconciliation failed unexpectedly",
    ]:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Checkout failing"},
    ).json()

    response = client.post(f"/incidents/{incident['id']}/analyze")
    assert response.status_code == 201
    analysis = response.json()

    # 最终证据 = 规则证据 + 关键词命中日志，[E#] 编号映射持久化
    assert len(analysis["final_evidence_log_ids"]) == 2
    evidence = analysis["evidence_logs"]
    assert len(evidence) == 2
    by_message = {e["log_entry"]["message"]: e["reason"] for e in evidence}
    assert by_message[
        "DBConnectionTimeout while connecting to mysql-primary"
    ] == "Matched database_issue rule."
    assert by_message[
        "ERROR inventory reconciliation failed unexpectedly"
    ] == "Agent keyword search match."

    # 调查笔记（[N#] 映射）与缺失信息落库
    assert analysis["investigation_notes"], "agent 调查笔记必须持久化"
    assert isinstance(analysis["missing_information"], list)

    # API 重载路径同样保留
    reloaded = client.get(f"/incidents/{incident['id']}/analysis").json()
    assert reloaded["final_evidence_log_ids"] == analysis["final_evidence_log_ids"]
    assert reloaded["investigation_notes"] == analysis["investigation_notes"]
