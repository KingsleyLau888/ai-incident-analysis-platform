"""API routes — REST endpoints, SSE streaming, and dashboard."""

import asyncio
import json
import time
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.schemas.analysis import AnalysisRunRead, AnalysisTraceRead
from app.schemas.analysis_job import AnalysisJobRead
from app.schemas.feedback import FeedbackCreate, FeedbackRead
from app.schemas.incident import IncidentCreate, IncidentRead
from app.schemas.log_entry import ExternalLogCreate, LogEntryCreate, LogEntryRead
from app.schemas.service import ServiceCreate, ServiceRead
from app.services import (
    analysis_service,
    analysis_job_service,
    automatic_incident_service,
    feedback_service,
    incident_service,
    log_service,
    service_service,
)

router = APIRouter()

# Dashboard templates
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")


# ═══════════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
# Feature status — tells the dashboard what's active
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/features")
def get_features():
    """Return which advanced features are currently active."""
    return analysis_service.detect_features()


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard (HTML pages)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page — create services, logs, incidents, and analyze."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/dev-tools", response_class=HTMLResponse)
def dev_tools(request: Request):
    return templates.TemplateResponse("dev_tools.html", {"request": request})


def _build_snapshot(db: Session) -> dict:
    """构建 SSE 快照：服务全量；事故/日志/任务在数据库侧限额 50 条（F14）。"""
    return {
        "services": [
            ServiceRead.model_validate(item).model_dump(mode="json")
            for item in service_service.list_services(db)
        ],
        "incidents": [
            IncidentRead.model_validate(item).model_dump(mode="json")
            for item in incident_service.list_incidents(db, limit=50)
        ],
        "logs": [
            LogEntryRead.model_validate(item).model_dump(mode="json")
            for item in log_service.list_log_entries(db, limit=50)
        ],
        "jobs": [
            AnalysisJobRead.model_validate(item).model_dump(mode="json")
            for item in analysis_job_service.list_jobs(db, limit=50)
        ],
    }


@router.get("/events")
async def platform_events():
    """Publish live services, logs, incidents, and analysis jobs."""

    async def event_stream() -> AsyncGenerator[str, None]:
        while True:
            # 每轮开新会话：查询后即释放 SQLite 读锁，避免长期连接阻塞写入
            with SessionLocal() as event_db:
                yield _sse_event("snapshot", _build_snapshot(event_db))
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Services
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(service_in: ServiceCreate, db: Session = Depends(get_db)):
    try:
        return service_service.create_service(db, service_in)
    except IntegrityError:
        # 同名（含并发）注册：明确 409，而不是 500（F03）
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Service name already exists"
        )


@router.get("/services", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db)):
    return service_service.list_services(db)


@router.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = service_service.get_service(db, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


# ═══════════════════════════════════════════════════════════════════════════════
# Logs
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/logs", response_model=LogEntryRead, status_code=status.HTTP_201_CREATED)
def create_log_entry(
    log_in: LogEntryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if service_service.get_service(db, log_in.service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    log_entry = log_service.create_log_entry(db, log_in)
    incident, job_id = automatic_incident_service.process_log_entry(db, log_entry)
    if incident is not None and job_id is not None:
        background_tasks.add_task(
            automatic_incident_service.analyze_incident_in_background,
            db.get_bind(),
            job_id,
        )
    return log_entry


@router.post("/ingest/logs", response_model=LogEntryRead, status_code=status.HTTP_201_CREATED)
def ingest_external_log(
    log_in: ExternalLogCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    service = next(
        (item for item in service_service.list_services(db) if item.name == log_in.service_name),
        None,
    )
    if service is None:
        try:
            service = service_service.create_service(
                db,
                ServiceCreate(name=log_in.service_name, description="Automatically registered"),
            )
        except IntegrityError:
            # 并发注册同名服务：回滚后归到已存在的服务（F03）
            db.rollback()
            service = next(
                (
                    item
                    for item in service_service.list_services(db)
                    if item.name == log_in.service_name
                ),
                None,
            )
            if service is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Service registration conflict, retry later",
                )
    log_entry = log_service.create_log_entry(
        db,
        LogEntryCreate(
            service_id=service.id,
            level=log_in.level,
            message=log_in.message,
            timestamp=log_in.timestamp,
        ),
    )
    incident, job_id = automatic_incident_service.process_log_entry(db, log_entry)
    if incident is not None and job_id is not None:
        background_tasks.add_task(analysis_job_service.run_job, db.get_bind(), job_id)
    return log_entry


@router.get("/logs", response_model=list[LogEntryRead])
def list_log_entries(
    service_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return log_service.list_log_entries(db, service_id=service_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Incidents
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(incident_in: IncidentCreate, db: Session = Depends(get_db)):
    if service_service.get_service(db, incident_in.service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return incident_service.create_incident(db, incident_in)


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    service_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return incident_service.list_incidents(db, service_id=service_id)


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.post(
    "/incidents/{incident_id}/analysis-jobs",
    response_model=AnalysisJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_analysis_job(
    incident_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    # 防连点（F02）：已有排队中/进行中的任务时复用原任务；
    # 已完成的任务不拦——再次触发视为有意重分析，会新建任务。
    job = analysis_job_service.find_active_job(db, incident_id)
    if job is None:
        try:
            job = analysis_job_service.create_job(db, incident_id, trigger="manual")
        except IntegrityError:
            # 并发先查后建竞态：唯一索引兜底，回滚后取已有活动任务（F03）
            db.rollback()
            job = analysis_job_service.find_active_job(db, incident_id)
            if job is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An analysis job is already active for this incident",
                )
    # 对复用任务补一次执行是安全的：领取是原子条件更新，重复触发不产生重复结果
    background_tasks.add_task(analysis_job_service.run_job, db.get_bind(), job.id)
    return job


@router.get("/analysis-jobs", response_model=list[AnalysisJobRead])
def list_analysis_jobs(
    incident_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return analysis_job_service.list_jobs(db, incident_id=incident_id)


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobRead)
def get_analysis_job(job_id: int, db: Session = Depends(get_db)):
    job = analysis_job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return job


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis (standard + SSE streaming)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=AnalysisRunRead,
    status_code=status.HTTP_201_CREATED,
)
def analyze_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    # 手动分析也建任务（F03）：任务列表完整、Dashboard 经 job 感知新结果
    try:
        job = analysis_job_service.create_job(db, incident_id, trigger="manual")
    except IntegrityError:
        # 每事故同时最多一个未完成任务（唯一索引）：冲突时明确 409
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An analysis job is already active for this incident",
        )
    analysis = analysis_job_service.execute_job(db, job.id)
    if analysis is None:
        job = analysis_job_service.get_job(db, job.id)
        detail = (job.error if job is not None else "Analysis failed.")[:500]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {detail}"
        )
    return analysis


@router.post("/incidents/{incident_id}/analyze/stream")
async def analyze_incident_stream(incident_id: int, db: Session = Depends(get_db)):
    """Stream the analysis process as Server-Sent Events.

    分析在工作线程运行（不阻塞事件循环）；progress_callback 的每一步
    经线程安全队列变成实时 progress 事件；诊断文本在完成后一次性发送
    并标注 simulated（本系统无真实 token 流，不伪装逐字生成）（F14）。
    手动流式分析也建任务并走统一执行入口：任务状态与流一致，失败时
    任务标 failed 并如实发 error 事件后结束，不半路断流（F03）。
    """
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    # 释放 404 检查事务：工作线程在同一连接上另行开事务（单连接池场景下避免嵌套）
    db.rollback()

    try:
        job = analysis_job_service.create_job(db, incident_id, trigger="manual")
    except IntegrityError:
        # 每事故同时最多一个未完成任务（唯一索引）：冲突时明确 409
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An analysis job is already active for this incident",
        )
    job_id = job.id

    loop = asyncio.get_running_loop()
    progress_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    def run_analysis_in_thread() -> dict:
        """工作线程：独立会话经统一入口执行任务，进度经队列回传。"""
        with Session(bind=db.get_bind()) as worker_db:
            analysis = analysis_job_service.execute_job(
                worker_db,
                job_id,
                extra_progress_callback=lambda step, detail: loop.call_soon_threadsafe(
                    progress_queue.put_nowait, (step, detail)
                ),
            )
            if analysis is None:
                job = analysis_job_service.get_job(worker_db, job_id)
                return {"error": job.error if job is not None else "Analysis failed."}
            return {
                "analysis_id": analysis.id,
                "issue_type": analysis.issue_type,
                "severity": analysis.severity,
                "impact_scope": analysis.impact_scope,
                "diagnosis_summary": analysis.diagnosis_summary,
                "root_cause_hypotheses": analysis.root_cause_hypotheses,
                "suggested_actions": analysis.structured_suggested_actions
                or [analysis.suggested_actions],
                "evidence_count": len(analysis.evidence_logs),
                "runbook_count": len(analysis.retrieved_runbook_chunks),
                "similar_incident_count": len(analysis.similar_incidents),
                "traces": [
                    {
                        "step_name": trace.step_name,
                        "step_order": trace.step_order,
                        "detail": trace.detail,
                    }
                    for trace in sorted(analysis.traces, key=lambda t: t.step_order)
                ],
            }

    async def event_stream() -> AsyncGenerator[str, None]:
        start = time.monotonic()
        analysis_task = asyncio.create_task(asyncio.to_thread(run_analysis_in_thread))
        try:
            # 1. 实时进度：分析每完成一步就发一条真实事件
            while True:
                if not progress_queue.empty():
                    step, detail = progress_queue.get_nowait()
                    yield _sse_event(
                        "progress",
                        {
                            "step": step,
                            "message": detail,
                            "elapsed_seconds": round(time.monotonic() - start, 2),
                        },
                    )
                    continue
                if analysis_task.done():
                    # 让已排队但尚未执行的回调先落地，避免丢最后一条进度
                    await asyncio.sleep(0)
                    if progress_queue.empty():
                        break
                    continue
                get_task = asyncio.create_task(progress_queue.get())
                done, _ = await asyncio.wait(
                    {get_task, analysis_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if get_task in done:
                    step, detail = get_task.result()
                    yield _sse_event(
                        "progress",
                        {
                            "step": step,
                            "message": detail,
                            "elapsed_seconds": round(time.monotonic() - start, 2),
                        },
                    )
                else:
                    get_task.cancel()
                    await asyncio.gather(get_task, return_exceptions=True)

            result = analysis_task.result()
            if "error" in result:
                # 任务已标 failed：如实发 error 事件后结束，不半路断流（F03）
                yield _sse_event("error", {"message": result["error"]})
                return

            # 2. 诊断摘要（一次发送；无真实 token 流，如实标注 simulated）
            yield _sse_event(
                "diagnosis_chunk",
                {"field": "summary", "text": result["diagnosis_summary"], "simulated": True},
            )

            # 3. 根因假设与建议操作（真实数据，非逐字模拟）
            for i, hypothesis in enumerate(result["root_cause_hypotheses"]):
                yield _sse_event("hypothesis", {
                    "index": i,
                    "cause": hypothesis.get("cause", ""),
                    "confidence": hypothesis.get("confidence", 0),
                })

            for action in result["suggested_actions"]:
                yield _sse_event("action", {"text": action})

            # 4. 真实 Trace
            for trace in result["traces"]:
                yield _sse_event("trace", {
                    "step_name": trace["step_name"],
                    "step_order": trace["step_order"],
                    "detail": trace["detail"],
                })

            # 5. 完成
            yield _sse_event("complete", {
                "analysis_id": result["analysis_id"],
                "issue_type": result["issue_type"],
                "severity": result["severity"],
                "impact_scope": result["impact_scope"],
                "evidence_count": result["evidence_count"],
                "runbook_count": result["runbook_count"],
                "similar_incident_count": result["similar_incident_count"],
            })
        finally:
            if not analysis_task.done():
                # 客户端断开：取消等待，后台线程仍会跑完分析并落库（与旧行为一致）
                analysis_task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/incidents/{incident_id}/analysis", response_model=AnalysisRunRead)
def get_incident_analysis(incident_id: int, db: Session = Depends(get_db)):
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    analysis = analysis_service.get_latest_analysis_for_incident(db, incident_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.get("/incidents/{incident_id}/trace", response_model=list[AnalysisTraceRead])
def get_incident_trace(incident_id: int, db: Session = Depends(get_db)):
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    analysis = analysis_service.get_latest_analysis_for_incident(db, incident_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return sorted(analysis.traces, key=lambda trace: trace.step_order)


# ═══════════════════════════════════════════════════════════════════════════════
# Feedback
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/analysis/{analysis_run_id}/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(analysis_run_id: int, feedback_in: FeedbackCreate, db: Session = Depends(get_db)):
    return feedback_service.upsert_feedback(db, analysis_run_id, feedback_in)


@router.get("/analysis/{analysis_run_id}/feedback", response_model=FeedbackRead)
def get_feedback(analysis_run_id: int, db: Session = Depends(get_db)):
    feedback = feedback_service.get_feedback(db, analysis_run_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return feedback


@router.get("/feedback", response_model=list[FeedbackRead])
def list_positive_feedback(min_rating: int = 4, db: Session = Depends(get_db)):
    return feedback_service.list_positive_feedback(db, min_rating=min_rating)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _sse_event(event: str, data: dict) -> str:
    """Format a dict as a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
