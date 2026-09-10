"""Small compatibility migrations for the SQLite prototype database."""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text


ANALYSIS_RUN_COLUMNS = {
    "retrieved_runbook_chunks": "JSON NOT NULL DEFAULT '[]'",
    "similar_incidents": "JSON NOT NULL DEFAULT '[]'",
    "analysis_plan": "JSON NOT NULL DEFAULT '{\"analysis_plan\":\"\",\"tool_steps\":[]}'",
    "diagnosis_summary": "TEXT NOT NULL DEFAULT ''",
    "root_cause_hypotheses": "JSON NOT NULL DEFAULT '[]'",
    "impact_scope": "TEXT NOT NULL DEFAULT ''",
    "structured_suggested_actions": "JSON NOT NULL DEFAULT '[]'",
}


def ensure_analysis_result_columns(engine: Engine) -> None:
    """Add persisted analysis fields to databases created by older versions."""
    inspector = inspect(engine)
    if "analysis_runs" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("analysis_runs")}
    missing = {
        name: definition
        for name, definition in ANALYSIS_RUN_COLUMNS.items()
        if name not in existing
    }
    if not missing:
        return

    with engine.begin() as connection:
        for name, definition in missing.items():
            connection.execute(
                text(f'ALTER TABLE analysis_runs ADD COLUMN "{name}" {definition}')
            )


def ensure_incident_dedupe_columns(engine: Engine) -> None:
    """F03：incidents 增加初步类型列（去重不依赖分析结果），并从历史分析回填。"""
    inspector = inspect(engine)
    if "incidents" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("incidents")}
    if "inferred_issue_type" not in existing:
        with engine.begin() as connection:
            connection.execute(
                text('ALTER TABLE incidents ADD COLUMN "inferred_issue_type" VARCHAR(80)')
            )

    # 老数据回填：取该事故最新一次分析的类型（幂等：只补 NULL 行）
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE incidents SET inferred_issue_type = ("
                "  SELECT issue_type FROM analysis_runs"
                "  WHERE analysis_runs.incident_id = incidents.id"
                "  ORDER BY analysis_runs.id DESC LIMIT 1"
                ") WHERE inferred_issue_type IS NULL"
            )
        )


def ensure_active_job_unique_index(engine: Engine) -> None:
    """F03：每事故最多一个未完成任务（pending/running）的部分唯一索引。"""
    inspector = inspect(engine)
    if "analysis_jobs" not in inspector.get_table_names():
        return

    index_names = {index["name"] for index in inspector.get_indexes("analysis_jobs")}
    if "uq_active_job_per_incident" in index_names:
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_job_per_incident "
                "ON analysis_jobs (incident_id) WHERE status IN ('pending','running')"
            )
        )
