"""Incident analysis service.

Orchestrates the full analysis pipeline — rule detection, evidence extraction,
multi-query retrieval with query rewriting, and structured diagnosis.

Modes (auto-detected):
    - Full pipeline (default): rule engine → query rewriting → multi-query
      retrieval → CrossEncoder re-rank → LLM diagnosis. Works with mock LLM.
    - ReAct Agent: LLM-driven dynamic investigation. Activated by REACT_AGENT_ENABLED=1.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.analysis_mode_router import AnalysisModeRouter
from app.agent.diagnosis_planner import DiagnosisPlanner
from app.agent.react_agent import AgentResult, ReActAgent
from app.llm.factory import get_llm_client
from app.models.analysis import AnalysisRun, AnalysisTrace, IncidentEvidence
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.rule_engine.detector import detect_issue, suggested_actions_for
from app.services.query_rewriter import rewrite_query
from app.services.rrf import reciprocal_rank_fusion
from app.services.runbook_retriever import (
    RunbookRetriever,
    RetrievedRunbookChunk,
    serialize_retrieved_chunks,
)
from app.services.similar_incident_retriever import (
    SimilarIncident,
    SimilarIncidentRetriever,
    serialize_similar_incidents,
)


class _AgentObservationLog:
    def __init__(self, message: str) -> None:
        self.id = 0
        self.level = "INFO"
        self.message = message
        self.timestamp = None

PIPELINE_TRACE_STEPS = (
    "log_filtering",
    "rule_detection",
    "evidence_selection",
    "analysis_mode_routing",
    "query_rewriting",
    "planner_decision",
    "vector_runbook_retrieval",
    "similar_incident_retrieval",
    "summary_generation",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Feature detection (for the /features API and trace)
# ═══════════════════════════════════════════════════════════════════════════════


def detect_features() -> dict[str, bool | str]:
    """Return which advanced features are currently active."""
    from app.services.embedding_service import (
        CROSS_ENCODER_ENABLED,
        get_cross_encoder,
        get_retrieval_mode,
        get_sentence_transformer_embedder,
    )

    retrieval_mode = get_retrieval_mode()
    has_dense = False
    if retrieval_mode in {"sentence-transformers", "hybrid", "chromadb"}:
        has_dense = get_sentence_transformer_embedder() is not None
    has_reranker = get_cross_encoder() is not None

    return {
        "retrieval_mode": retrieval_mode,
        "cross_encoder_enabled": CROSS_ENCODER_ENABLED and has_reranker,
        "query_rewriting_enabled": True,  # always active (template fallback)
        "query_rewriting_provider": "llm" if _has_real_llm() else "template",
        "analysis_mode": _requested_analysis_mode(),
        "react_agent_enabled": _agent_allowed(),
        "chromadb_available": retrieval_mode == "chromadb" and has_dense,
        "sentence_transformer_available": has_dense,
        "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
        "chunking_strategy": os.getenv("CHUNKING_STRATEGY", "markdown"),
    }


def _has_real_llm() -> bool:
    return os.getenv("LLM_PROVIDER") == "openai_compatible" and bool(
        os.getenv("LLM_API_KEY")
    )


def _log_window_start(
    db: Session,
    incident: Incident,
    incident_time,
    log_window_minutes: int,
):
    default_start = incident_time - timedelta(minutes=log_window_minutes)
    if not _is_automatic_incident(incident):
        return default_start

    previous_incident = db.scalars(
        select(Incident)
        .where(
            Incident.service_id == incident.service_id,
            Incident.id < incident.id,
        )
        .order_by(Incident.id.desc())
    ).first()
    if previous_incident is None:
        return default_start

    previous_time = previous_incident.created_at
    if previous_time.tzinfo is None:
        previous_time = previous_time.replace(tzinfo=UTC)
    return max(default_start, previous_time)


def _log_window_end(incident: Incident, incident_time):
    # F04：窗口统一以事故创建时刻封顶——自动事故如此，手动事故也如此，
    # 防止旧手动事故重分析混入创建之后的无关故障（source 为 NULL 的老数据
    # 由迁移按标题回填，此处 None 按 manual 语义封顶，宁可少取不混入）。
    return incident_time


def _is_automatic_incident(incident: Incident) -> bool:
    # F04：看出身字段，不再看标题前缀（改标题不再影响窗口语义）
    return incident.source == "automatic"


# ═══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════════


def analyze_incident(
    db: Session,
    incident: Incident,
    progress_callback: Callable[[str, str], None] | None = None,
) -> AnalysisRun:
    """Run the analysis pipeline (or ReAct agent) for *incident*."""
    log_window_minutes = int(os.getenv("ANALYSIS_LOG_WINDOW_MINUTES", "5"))
    incident_time = incident.created_at
    if incident_time.tzinfo is None:
        incident_time = incident_time.replace(tzinfo=UTC)
    window_start = _log_window_start(db, incident, incident_time, log_window_minutes)
    window_end = _log_window_end(incident, incident_time)
    log_filters = [
        LogEntry.service_id == incident.service_id,
        LogEntry.timestamp >= window_start,
    ]
    if window_end is not None:
        log_filters.append(LogEntry.timestamp <= window_end)
    logs = list(
        db.scalars(
            select(LogEntry)
            .where(*log_filters)
            .order_by(LogEntry.timestamp, LogEntry.id)
        ).all()
    )
    _report(progress_callback, "log_filtering", f"Selected {len(logs)} recent service logs.")

    detection = detect_issue(logs)
    _report(
        progress_callback,
        "rule_detection",
        (
            f"Detected {detection.issue_type} with severity {detection.severity}; "
            f"confidence={detection.confidence:.2f}."
        ),
    )
    service_name = incident.service.name if incident.service else f"service-{incident.service_id}"

    diagnosis_plan = DiagnosisPlanner().plan(
        incident_title=incident.title,
        service_name=service_name,
        issue_type=detection.issue_type,
        severity=detection.severity,
        evidence_logs=detection.evidence_logs,
    )
    _report(
        progress_callback,
        "planner_decision",
        f"Selected tools: {', '.join(diagnosis_plan.tool_steps)}.",
    )

    runbook_retriever = RunbookRetriever()
    similar_incident_retriever = SimilarIncidentRetriever(
        embedder=runbook_retriever.embedder,
        dense_embedder=runbook_retriever.dense_embedder,
        retrieval_mode=runbook_retriever.retrieval_mode,
    )

    features = detect_features()
    agent_client = _get_react_llm_client() if _agent_allowed() else None
    mode_decision = AnalysisModeRouter().route(
        incident_title=incident.title,
        logs=logs,
        detection=detection,
        requested_mode=_requested_analysis_mode(),
        agent_available=agent_client is not None,
    )

    # Choose analysis mode
    if mode_decision.mode == "agent":
        _report(progress_callback, "agent_investigation", mode_decision.reason)
        retrieved_runbook_chunks, similar_incidents, react_result, diagnosis_result = (
            _run_react_agent(
                incident=incident,
                service_name=service_name,
                detection=detection,
                logs=logs,
                runbook_retriever=runbook_retriever,
                similar_incident_retriever=similar_incident_retriever,
                llm_client=agent_client,
            )
        )
    else:
        _report(
            progress_callback,
            "knowledge_retrieval",
            "Rewriting queries and retrieving runbooks and similar incidents.",
        )
        retrieved_runbook_chunks, similar_incidents, react_result, diagnosis_result = (
            _run_pipeline(
                incident=incident,
                service_name=service_name,
                detection=detection,
                logs=logs,
                runbook_retriever=runbook_retriever,
                similar_incident_retriever=similar_incident_retriever,
                diagnosis_plan=diagnosis_plan,
                features=features,
            )
        )

    structured_diagnosis = diagnosis_result.diagnosis
    _report(
        progress_callback,
        "summary_generation",
        f"Structured diagnosis generated by {diagnosis_result.provider}.",
    )
    summary = f"Detected {detection.issue_type} in {service_name} based on related error logs."

    analysis_run = AnalysisRun(
        incident_id=incident.id,
        issue_type=detection.issue_type,
        severity=detection.severity,
        root_cause_summary=summary,
        suggested_actions=suggested_actions_for(detection.issue_type),
    )
    analysis_run.set_retrieved_runbook_chunks(serialize_retrieved_chunks(retrieved_runbook_chunks))
    analysis_run.set_similar_incidents(serialize_similar_incidents(similar_incidents))
    plan_text, tool_steps = _analysis_plan_from_result(
        diagnosis_plan=diagnosis_plan,
        react_result=react_result,
        incident_title=incident.title,
        service_name=service_name,
    )
    analysis_run.set_analysis_plan(plan_text, tool_steps)
    analysis_run.set_structured_diagnosis(
        diagnosis_summary=structured_diagnosis.diagnosis_summary,
        root_cause_hypotheses=[
            hypothesis.model_dump() for hypothesis in structured_diagnosis.root_cause_hypotheses
        ],
        impact_scope=structured_diagnosis.impact_scope,
        structured_suggested_actions=structured_diagnosis.structured_suggested_actions,
    )
    db.add(analysis_run)
    db.flush()
    # 注意：此处不发进度消息。结果、证据、Trace 必须一次提交（原子性），
    # 进度回调内部会 commit，若在此处发消息会提前提交半成品 AnalysisRun（F01）。

    for log in detection.evidence_logs:
        db.add(
            IncidentEvidence(
                analysis_run_id=analysis_run.id,
                log_entry_id=log.id,
                reason=f"Matched {detection.issue_type} rule.",
            )
        )

    # Build trace
    if react_result is not None:
        _persist_react_trace(
            db, analysis_run.id, react_result, logs, detection, diagnosis_result, mode_decision
        )
    else:
        _persist_pipeline_trace(
            db, analysis_run.id, logs, detection, diagnosis_plan,
            retrieved_runbook_chunks, similar_incidents, diagnosis_result,
            runbook_retriever, similar_incident_retriever, features, mode_decision,
        )

    db.commit()
    # 提交完成后才汇报进度：此时结果、证据、Trace 已整体落盘，
    # 进度回调内部的 commit 只会提交 job 行，不会泄漏半成品（F01）。
    _report(progress_callback, "persistence", "Evidence, diagnosis, and trace persisted.")
    saved_analysis_run = get_analysis_run(db, analysis_run.id)
    if saved_analysis_run is not None:
        saved_analysis_run.set_retrieved_runbook_chunks(serialize_retrieved_chunks(retrieved_runbook_chunks))
        saved_analysis_run.set_similar_incidents(serialize_similar_incidents(similar_incidents))
        saved_analysis_run.set_analysis_plan(plan_text, tool_steps)
        saved_analysis_run.set_structured_diagnosis(
            diagnosis_summary=structured_diagnosis.diagnosis_summary,
            root_cause_hypotheses=[
                hypothesis.model_dump() for hypothesis in structured_diagnosis.root_cause_hypotheses
            ],
            impact_scope=structured_diagnosis.impact_scope,
            structured_suggested_actions=structured_diagnosis.structured_suggested_actions,
        )
    return saved_analysis_run


def _report(
    callback: Callable[[str, str], None] | None,
    step: str,
    detail: str,
) -> None:
    if callback is not None:
        callback(step, detail)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline mode (with Query Rewriting + multi-query retrieval)
# ═══════════════════════════════════════════════════════════════════════════════


def _pipeline_variant_top_k() -> int:
    """多查询融合前每个变体的检索条数（RRF 融合输入宽度）。

    默认 5（历史行为），可用 PIPELINE_VARIANT_TOP_K 调大以扩大具体手册的召回。
    """
    try:
        value = int(os.getenv("PIPELINE_VARIANT_TOP_K", "5"))
    except ValueError:
        return 5
    return value if value >= 1 else 5


def _pipeline_rrf_k() -> int:
    """RRF 融合常数 k（默认 60，历史行为）。

    调大压缩名次差异、奖励多列表共识，可用 RRF_K 实验。
    """
    try:
        value = int(os.getenv("RRF_K", "60"))
    except ValueError:
        return 60
    return value if value >= 1 else 60


def _run_pipeline(   # 这是一个pipeline，首先是提取证据文本
    incident,
    service_name,
    detection,
    logs,
    runbook_retriever,
    similar_incident_retriever,
    diagnosis_plan,
    features,
):
    """Pipeline with Query Rewriting → multi-query retrieval → RRF fusion."""
    # 去重：错误风暴产生同文案日志，重复消息会虚增查询词权重
    evidence_text = " ".join(dict.fromkeys(log.message for log in detection.evidence_logs))

    # --- Query Rewriting ---
    rewritten = rewrite_query(
        incident_title=incident.title,
        service_name=service_name,
        issue_type=detection.issue_type,
        evidence_text=evidence_text,
    )

    # --- Multi-query Runbook Retrieval ---
    if "retrieve_runbooks" in diagnosis_plan.tool_steps:
        if len(rewritten.variants) > 1:
            # Multi-query: retrieve independently for each variant, fuse with RRF
            variant_top_k = _pipeline_variant_top_k()
            all_ranked: list[list[tuple[int, float]]] = []
            for variant in rewritten.variants:
                ranked = runbook_retriever._rank(
                    variant,
                    [f"{c.source}\n{c.title}\n{c.content}" for c in runbook_retriever.chunks],
                    top_k=variant_top_k,
                    issue_type=detection.issue_type,
                )
                all_ranked.append(ranked)
            fused = reciprocal_rank_fusion(
                all_ranked,
                key=lambda item: item[0],
                k=_pipeline_rrf_k(),
            )
            top_indices = [
                (result.item[0], result.score) for result in fused[:3]
            ]
            retrieved_runbook_chunks = [
                RetrievedRunbookChunk(
                    chunk_id=runbook_retriever.chunks[idx].chunk_id,
                    source=runbook_retriever.chunks[idx].source,
                    title=runbook_retriever.chunks[idx].title,
                    content=runbook_retriever.chunks[idx].content,
                    score=round(score, 6),
                )
                for idx, score in top_indices
            ]
        else:
            retrieved_runbook_chunks = runbook_retriever.retrieve(
                incident_title=incident.title,
                service_name=service_name,
                evidence_logs=detection.evidence_logs,
                issue_type=detection.issue_type,
            )
    else:
        retrieved_runbook_chunks = []

    # --- Multi-query Similar Incident Retrieval ---
    if "retrieve_similar_incidents" in diagnosis_plan.tool_steps:
        if len(rewritten.variants) > 1:
            all_ranked: list[list[tuple[int, float]]] = []
            inc_docs = [_incident_doc(inc) for inc in similar_incident_retriever.incidents]
            for variant in rewritten.variants:
                ranked = similar_incident_retriever._rank(variant, inc_docs, top_k=_pipeline_variant_top_k())
                all_ranked.append(ranked)
            fused = reciprocal_rank_fusion(all_ranked, key=lambda item: item[0], k=_pipeline_rrf_k())
            top_indices = [(result.item[0], result.score) for result in fused[:3]]
            similar_incidents = [
                SimilarIncident(
                    historical_id=similar_incident_retriever.incidents[idx].historical_id,
                    title=similar_incident_retriever.incidents[idx].title,
                    issue_type=similar_incident_retriever.incidents[idx].issue_type,
                    similarity_score=round(score, 6),
                    root_cause=similar_incident_retriever.incidents[idx].root_cause,
                    resolution=similar_incident_retriever.incidents[idx].resolution,
                )
                for idx, score in top_indices
            ]
        else:
            similar_incidents = similar_incident_retriever.retrieve(
                incident_title=incident.title,
                service_name=service_name,
                issue_type=detection.issue_type,
                evidence_logs=detection.evidence_logs,
            )
    else:
        similar_incidents = []

    diagnosis_result = get_llm_client().diagnose(
        incident_title=incident.title,
        service_name=service_name,
        issue_type=detection.issue_type,
        severity=detection.severity,
        evidence_logs=detection.evidence_logs,
        retrieved_runbook_chunks=retrieved_runbook_chunks,
        similar_incidents=similar_incidents,
    )
    return retrieved_runbook_chunks, similar_incidents, None, diagnosis_result


def _incident_doc(incident) -> str:
    return "\n".join([
        incident.historical_id, incident.title, incident.service_name,
        incident.issue_type, " ".join(incident.symptoms),
        incident.root_cause, incident.resolution, " ".join(incident.tags),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ReAct Agent mode
# ═══════════════════════════════════════════════════════════════════════════════


def _requested_analysis_mode() -> str:
    explicit = os.getenv("ANALYSIS_MODE")
    if explicit:
        return explicit.strip().lower()
    if os.getenv("REACT_AGENT_ENABLED", "0").strip().lower() in {"1", "true", "yes"}:
        return "agent"
    return "auto"


def _agent_allowed() -> bool:
    return _requested_analysis_mode() in {"auto", "agent"}


def _run_react_agent(
    incident, service_name, detection, logs,
    runbook_retriever, similar_incident_retriever, llm_client,
):
    def search_logs_fn(ctx): return logs
    def detect_signals_fn(ctx):
        d = detect_issue(ctx.get("logs", logs))
        return {"issue_type": d.issue_type, "severity": d.severity,
                "matched_issues": d.matched_issues, "evidence_logs": d.evidence_logs,
                "confidence": d.confidence, "candidate_scores": d.candidate_scores or {}}
    def retrieve_runbooks_fn(query, top_k):
        return runbook_retriever.retrieve(
            incident_title=incident.title, service_name=service_name,
            evidence_logs=detection.evidence_logs, issue_type=detection.issue_type,
            top_k=top_k)
    def retrieve_similar_incidents_fn(query, top_k):
        return similar_incident_retriever.retrieve(
            incident_title=incident.title, service_name=service_name,
            issue_type=detection.issue_type, evidence_logs=detection.evidence_logs,
            top_k=top_k)
    def generate_diagnosis_fn(ctx):
        evidence_logs = list(ctx.get("evidence_logs", detection.evidence_logs))
        evidence_logs.extend(
            _AgentObservationLog(f"Agent investigation note: {note}")
            for note in ctx.get("investigation_notes", [])
        )
        return get_llm_client().diagnose(
            incident_title=incident.title, service_name=service_name,
            issue_type=ctx.get("issue_type", detection.issue_type),
            severity=ctx.get("severity", detection.severity),
            evidence_logs=evidence_logs,
            retrieved_runbook_chunks=ctx.get("runbook_chunks", []),
            similar_incidents=ctx.get("similar_incidents", []))

    agent = ReActAgent(llm_client=llm_client)
    result = agent.investigate(
        incident_title=incident.title, service_name=service_name,
        search_logs_fn=search_logs_fn, detect_signals_fn=detect_signals_fn,
        retrieve_runbooks_fn=retrieve_runbooks_fn,
        retrieve_similar_incidents_fn=retrieve_similar_incidents_fn,
        generate_diagnosis_fn=generate_diagnosis_fn)

    final_context = result.final_context or {}
    retrieved = final_context.get("runbook_chunks", [])
    sim = final_context.get("similar_incidents", [])
    diagnosis_result = result.final_diagnosis or generate_diagnosis_fn(final_context)
    return retrieved, sim, result, diagnosis_result


def _get_react_llm_client():
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider != "openai_compatible": return None
    try:
        from app.llm.openai_compatible_client import OpenAICompatibleClient
        return OpenAICompatibleClient(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", ""))
    except Exception: return None


def _analysis_plan_from_result(
    diagnosis_plan,
    react_result: AgentResult | None,
    incident_title: str,
    service_name: str,
) -> tuple[str, list[str]]:
    if react_result is None:
        return diagnosis_plan.analysis_plan, diagnosis_plan.tool_steps

    tool_steps = [
        step.action for step in react_result.steps
        if step.action is not None
    ]
    plan_text = (
        f"ReAct agent investigated '{incident_title}' for {service_name}. "
        f"It selected tools dynamically via {react_result.provider}: "
        f"{', '.join(tool_steps)}."
    )
    return plan_text, tool_steps


# ═══════════════════════════════════════════════════════════════════════════════
# Trace persistence
# ═══════════════════════════════════════════════════════════════════════════════


def _persist_react_trace(
    db, analysis_run_id, react_result, logs, detection, diagnosis_result, mode_decision
):
    steps_data = [
        ("analysis_mode_routing", 0,
         f"selected_mode=agent; reason={mode_decision.reason}."),
        ("react_agent_context", 1,
         f"Agent mode: {react_result.provider}; total_steps={len(react_result.steps)}; "
         f"logs_count={len(logs)}; issue_type={detection.issue_type}; "
         f"confidence={detection.confidence:.2f}"),
    ]
    for step in react_result.steps:
        detail = " | ".join(filter(None, [
            f"Thought: {step.thought}",
            f"Action: {step.action}" if step.action else "",
            f"Input: {step.action_input}" if step.action_input else "",
            f"Observation: {step.observation}",
        ]))
        steps_data.append((f"react_step_{step.step_number}", step.step_number + 1, detail))
    steps_data.append(
        ("summary_generation", len(react_result.steps) + 2,
         f"Generated structured diagnosis; provider={diagnosis_result.provider}."))
    for step_name, step_order, detail in steps_data:
        db.add(AnalysisTrace(analysis_run_id=analysis_run_id, step_name=step_name,
                             step_order=step_order, detail=detail))


def _persist_pipeline_trace(
    db, analysis_run_id, logs, detection, diagnosis_plan,
    retrieved_runbook_chunks, similar_incidents, diagnosis_result,
    runbook_retriever, similar_incident_retriever, features, mode_decision,
):
    from app.services.embedding_service import get_last_retrieval_timing

    timing = get_last_retrieval_timing()
    rerank_info = ""
    if timing.get("reranker") and timing["reranker"] != "none":
        rerank_info = f" rerank={timing['reranker']}({timing.get('rerank_ms', 0):.0f}ms)"

    trace_details = {
        "log_filtering": f"Selected {len(logs)} logs for service.",
        "rule_detection": (
            f"Detected issue_type={detection.issue_type}; "
            f"confidence={detection.confidence:.2f}; "
            f"matched={detection.matched_issues or ['unknown']}; "
            f"scores={detection.candidate_scores or {}}; "
            f"signals={detection.matched_signals or []}."
        ),
        "evidence_selection": (
            f"Selected {len(detection.evidence_logs)} direct and related evidence logs."
        ),
        "analysis_mode_routing": f"selected_mode={mode_decision.mode}; reason={mode_decision.reason}.",
        "query_rewriting": f"Query rewriting: provider={features['query_rewriting_provider']}, variants={','.join(features.get('_rewritten_variants', ['(original)']))}.",
        "planner_decision": f"Planner selected tool_steps={diagnosis_plan.tool_steps}.",
        "vector_runbook_retrieval": f"Retrieved {len(retrieved_runbook_chunks)} runbook chunks; {runbook_retriever.retrieval_detail}{rerank_info}.",
        "similar_incident_retrieval": f"Retrieved {len(similar_incidents)} similar incidents; {similar_incident_retriever.retrieval_detail}{rerank_info}.",
        "summary_generation": f"Generated structured diagnosis; provider={diagnosis_result.provider}.",
    }
    for index, step_name in enumerate(PIPELINE_TRACE_STEPS, start=1):
        db.add(AnalysisTrace(analysis_run_id=analysis_run_id, step_name=step_name,
                             step_order=index, detail=trace_details.get(step_name, "")))


# ═══════════════════════════════════════════════════════════════════════════════
# Query helpers
# ═══════════════════════════════════════════════════════════════════════════════


def get_latest_analysis_for_incident(db: Session, incident_id: int) -> AnalysisRun | None:
    return db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.incident_id == incident_id)
        .options(
            selectinload(AnalysisRun.evidence_logs).selectinload(IncidentEvidence.log_entry),
            selectinload(AnalysisRun.traces),
        )
        .order_by(AnalysisRun.id.desc())
    ).first()


def get_analysis_run(db: Session, analysis_run_id: int) -> AnalysisRun | None:
    return db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.id == analysis_run_id)
        .options(
            selectinload(AnalysisRun.evidence_logs).selectinload(IncidentEvidence.log_entry),
            selectinload(AnalysisRun.traces),
        )
    ).first()
