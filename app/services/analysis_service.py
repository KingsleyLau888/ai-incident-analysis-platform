from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agent.diagnosis_planner import DiagnosisPlanner
from app.llm.factory import get_llm_client
from app.models.analysis import AnalysisRun, AnalysisTrace, IncidentEvidence
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.rule_engine.detector import detect_issue, suggested_actions_for
from app.services.runbook_retriever import RunbookRetriever, serialize_retrieved_chunks
from app.services.similar_incident_retriever import SimilarIncidentRetriever, serialize_similar_incidents

TRACE_STEPS = (
    "log_filtering",
    "rule_detection",
    "evidence_selection",
    "planner_decision",
    "vector_runbook_retrieval",
    "similar_incident_retrieval",
    "summary_generation",
)


def analyze_incident(db: Session, incident: Incident) -> AnalysisRun:
    logs = list(
        db.scalars(
            select(LogEntry)
            .where(LogEntry.service_id == incident.service_id)
            .order_by(LogEntry.timestamp, LogEntry.id)
        ).all()
    ) #这里是根据传入的incident对象的service_id来查询相关的日志条目，并将它们存储在logs列表中。
    
    detection = detect_issue(logs)
    service_name = incident.service.name if incident.service else f"service-{incident.service_id}"
    diagnosis_plan = DiagnosisPlanner().plan(
        incident_title=incident.title,
        service_name=service_name,
        issue_type=detection.issue_type,
        severity=detection.severity,
        evidence_logs=detection.evidence_logs,
    )

    runbook_retriever = RunbookRetriever()
    retrieved_runbook_chunks = (
        runbook_retriever.retrieve(
            incident_title=incident.title,
            service_name=service_name,
            evidence_logs=detection.evidence_logs,
            issue_type=detection.issue_type,
        )
        if "retrieve_runbooks" in diagnosis_plan.tool_steps
        else []
    )
    similar_incident_retriever = SimilarIncidentRetriever(
        embedder=runbook_retriever.embedder,
        dense_embedder=runbook_retriever.dense_embedder,
        retrieval_mode=runbook_retriever.retrieval_mode,
    )
    similar_incidents = (
        similar_incident_retriever.retrieve(
            incident_title=incident.title,
            service_name=service_name,
            issue_type=detection.issue_type,
            evidence_logs=detection.evidence_logs,
        )
        if "retrieve_similar_incidents" in diagnosis_plan.tool_steps
        else []
    )
    diagnosis_result = get_llm_client().diagnose(
        incident_title=incident.title,
        service_name=service_name,
        issue_type=detection.issue_type,
        severity=detection.severity,
        evidence_logs=detection.evidence_logs,
        retrieved_runbook_chunks=retrieved_runbook_chunks,
        similar_incidents=similar_incidents,
    )
    structured_diagnosis = diagnosis_result.diagnosis
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
    analysis_run.set_analysis_plan(diagnosis_plan.analysis_plan, diagnosis_plan.tool_steps)
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

    for log in detection.evidence_logs:
        db.add(
            IncidentEvidence(
                analysis_run_id=analysis_run.id,
                log_entry_id=log.id,
                reason=f"Matched {detection.issue_type} rule.",
            )
        )

    trace_details = {
        "log_filtering": f"Selected {len(logs)} logs for service_id={incident.service_id}.",
        "rule_detection": f"Detected issue_type={detection.issue_type}; matched={detection.matched_issues or ['unknown']}.",
        "evidence_selection": f"Selected {len(detection.evidence_logs)} evidence logs.",
        "planner_decision": f"Planner selected tool_steps={diagnosis_plan.tool_steps}.",
        "vector_runbook_retrieval": f"Retrieved {len(retrieved_runbook_chunks)} runbook chunks for issue_type={detection.issue_type}; {runbook_retriever.retrieval_detail}.",
        "similar_incident_retrieval": f"Retrieved {len(similar_incidents)} similar incidents for issue_type={detection.issue_type}; {similar_incident_retriever.retrieval_detail}.",
        "summary_generation": f"Generated legacy template summary plus structured diagnosis; provider={diagnosis_result.provider}.",
    }
    for index, step_name in enumerate(TRACE_STEPS, start=1):
        db.add(
            AnalysisTrace(
                analysis_run_id=analysis_run.id,
                step_name=step_name,
                step_order=index,
                detail=trace_details[step_name],
            )
        )

    db.commit()
    saved_analysis_run = get_analysis_run(db, analysis_run.id)
    if saved_analysis_run is not None:
        saved_analysis_run.set_retrieved_runbook_chunks(serialize_retrieved_chunks(retrieved_runbook_chunks))
        saved_analysis_run.set_similar_incidents(serialize_similar_incidents(similar_incidents))
        saved_analysis_run.set_analysis_plan(diagnosis_plan.analysis_plan, diagnosis_plan.tool_steps)
        saved_analysis_run.set_structured_diagnosis(
            diagnosis_summary=structured_diagnosis.diagnosis_summary,
            root_cause_hypotheses=[
                hypothesis.model_dump() for hypothesis in structured_diagnosis.root_cause_hypotheses
            ],
            impact_scope=structured_diagnosis.impact_scope,
            structured_suggested_actions=structured_diagnosis.structured_suggested_actions,
        )
    return saved_analysis_run


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
