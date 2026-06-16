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
