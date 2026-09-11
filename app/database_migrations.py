"""Small compatibility migrations for the SQLite prototype database."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, inspect, text


ANALYSIS_RUN_COLUMNS = {
    "retrieved_runbook_chunks": "JSON NOT NULL DEFAULT '[]'",
    "similar_incidents": "JSON NOT NULL DEFAULT '[]'",
    "analysis_plan": "JSON NOT NULL DEFAULT '{\"analysis_plan\":\"\",\"tool_steps\":[]}'",
    "diagnosis_summary": "TEXT NOT NULL DEFAULT ''",
    "root_cause_hypotheses": "JSON NOT NULL DEFAULT '[]'",
    "impact_scope": "TEXT NOT NULL DEFAULT ''",
    "structured_suggested_actions": "JSON NOT NULL DEFAULT '[]'",
    # R03（2026-09-11 复核）：模型声明的不确定信息 + 最终上下文快照
    "missing_information": "JSON NOT NULL DEFAULT '[]'",
    "investigation_notes": "JSON NOT NULL DEFAULT '[]'",
    "final_evidence_log_ids": "JSON NOT NULL DEFAULT '[]'",
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


_STORED_TIMESTAMP_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?([+-]\d{2}:\d{2})?$"
)


def ensure_log_time_columns(engine: Engine) -> dict[str, int]:
    """F04：log_entries 加 received_at 列（送达时间），并把 timestamp 归一为 UTC 文本。

    SQLite 按存储文本比较时间：混合 +08:00 与无时区字符串会让同一时刻排序错乱。
    因此逐行解析存量 timestamp（SQLAlchemy 存储格式），统一改写为 UTC 标准文本；
    无时区的老行按 UTC 理解（写入约定）。解析不了的行原样保留并计数上报。
    """
    inspector = inspect(engine)
    if "log_entries" not in inspector.get_table_names():
        return {}

    existing = {column["name"] for column in inspector.get_columns("log_entries")}
    added_column = 0
    if "received_at" not in existing:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE log_entries ADD COLUMN "received_at" DATETIME'))
        added_column = 1

    normalized = 0
    unchanged = 0
    unparseable = 0
    with engine.begin() as connection:
        rows = connection.execute(text("SELECT id, timestamp FROM log_entries")).fetchall()
        for row_id, stored in rows:
            if stored is None:
                continue
            parsed = _parse_stored_datetime(stored)
            if parsed is None:
                unparseable += 1
                continue
            canonical = _format_utc_text(parsed)
            if canonical == stored:
                unchanged += 1
                continue
            connection.execute(
                text("UPDATE log_entries SET timestamp = :value WHERE id = :row_id"),
                {"value": canonical, "row_id": row_id},
            )
            normalized += 1

    # 老数据回填：送达时间未知，用归一后的事件时间近似（文档已注明为近似值）
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE log_entries SET received_at = timestamp WHERE received_at IS NULL")
        )

    return {
        "added_column": added_column,
        "normalized": normalized,
        "unchanged": unchanged,
        "unparseable": unparseable,
    }


def _parse_stored_datetime(stored: str) -> datetime | None:
    """解析 SQLAlchemy SQLite DateTime 存储文本；无时区后缀按 UTC 理解。"""
    match = _STORED_TIMESTAMP_RE.match(stored)
    if match is None:
        return None
    year, month, day, hour, minute, second, microsecond, offset = match.groups()
    try:
        dt = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            int(microsecond.ljust(6, "0")) if microsecond else 0,
        )
    except ValueError:
        return None
    if offset is None:
        return dt.replace(tzinfo=UTC)
    sign = 1 if offset[0] == "+" else -1
    offset_minutes = sign * (int(offset[1:3]) * 60 + int(offset[4:6]))
    return dt.replace(tzinfo=UTC) - timedelta(minutes=offset_minutes)


def _format_utc_text(dt: datetime) -> str:
    """UTC 标准存储文本：与 ORM 自身写入格式一致（无偏移后缀的 UTC 墙钟文本）。

    本版本 SQLAlchemy 的 SQLite DateTime 会丢掉偏移量、按墙钟字段存储，
    所以统一为无后缀 UTC 墙钟，避免同一列混两种文本导致同刻比较错乱。
    """
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def ensure_incident_source_column(engine: Engine) -> dict[str, int]:
    """F04：incidents 加 source 列（automatic/manual），老数据按标题前缀回填。"""
    inspector = inspect(engine)
    if "incidents" not in inspector.get_table_names():
        return {}

    existing = {column["name"] for column in inspector.get_columns("incidents")}
    added_column = 0
    if "source" not in existing:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE incidents ADD COLUMN "source" VARCHAR(20)'))
        added_column = 1

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE incidents SET source = CASE "
                "  WHEN title LIKE 'Automatic alert for %' THEN 'automatic' "
                "  ELSE 'manual' END "
                "WHERE source IS NULL"
            )
        )
    return {"added_column": added_column}


# 外键体检（F15 收尾）：检查名 → (涉及的表, 孤儿计数 SQL)。
# 只统计已存在的表；孤儿数据本身不删除，先报告由人决定。
_ORPHAN_CHECKS: dict[str, tuple[set[str], str]] = {
    "log_entries_without_service": (
        {"log_entries", "services"},
        "SELECT COUNT(*) FROM log_entries l LEFT JOIN services s ON s.id = l.service_id "
        "WHERE s.id IS NULL",
    ),
    "incidents_without_service": (
        {"incidents", "services"},
        "SELECT COUNT(*) FROM incidents i LEFT JOIN services s ON s.id = i.service_id "
        "WHERE s.id IS NULL",
    ),
    "analysis_runs_without_incident": (
        {"analysis_runs", "incidents"},
        "SELECT COUNT(*) FROM analysis_runs r LEFT JOIN incidents i ON i.id = r.incident_id "
        "WHERE i.id IS NULL",
    ),
    "analysis_jobs_without_incident": (
        {"analysis_jobs", "incidents"},
        "SELECT COUNT(*) FROM analysis_jobs j LEFT JOIN incidents i ON i.id = j.incident_id "
        "WHERE i.id IS NULL",
    ),
    "analysis_jobs_without_run": (
        {"analysis_jobs", "analysis_runs"},
        "SELECT COUNT(*) FROM analysis_jobs j LEFT JOIN analysis_runs r ON r.id = j.analysis_run_id "
        "WHERE j.analysis_run_id IS NOT NULL AND r.id IS NULL",
    ),
    "analysis_traces_without_run": (
        {"analysis_traces", "analysis_runs"},
        "SELECT COUNT(*) FROM analysis_traces t LEFT JOIN analysis_runs r ON r.id = t.analysis_run_id "
        "WHERE r.id IS NULL",
    ),
    "incident_evidence_without_run": (
        {"incident_evidence", "analysis_runs"},
        "SELECT COUNT(*) FROM incident_evidence e LEFT JOIN analysis_runs r ON r.id = e.analysis_run_id "
        "WHERE r.id IS NULL",
    ),
    "incident_evidence_without_log": (
        {"incident_evidence", "log_entries"},
        "SELECT COUNT(*) FROM incident_evidence e LEFT JOIN log_entries l ON l.id = e.log_entry_id "
        "WHERE l.id IS NULL",
    ),
    "feedback_without_run": (
        {"diagnosis_feedback", "analysis_runs"},
        "SELECT COUNT(*) FROM diagnosis_feedback f LEFT JOIN analysis_runs r ON r.id = f.analysis_run_id "
        "WHERE r.id IS NULL",
    ),
}


def scan_foreign_key_orphans(engine: Engine) -> dict[str, int]:
    """体检每类外键的孤儿行数：开启外键检查前先报告，不擅自删除数据。"""
    tables = set(inspect(engine).get_table_names())
    result: dict[str, int] = {}
    with engine.connect() as connection:
        for name, (required_tables, statement) in _ORPHAN_CHECKS.items():
            if not required_tables.issubset(tables):
                continue
            result[name] = connection.execute(text(statement)).scalar() or 0
    return result
