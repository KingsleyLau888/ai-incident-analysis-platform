"""Tool definitions for the ReAct agent — callable functions that the agent
can invoke during diagnosis.

Each tool has a name, description, parameter schema, and execute function.
The agent sees the descriptions and decides which tool to call next.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters
    execute: Callable[..., Any]
    is_terminal: bool = False  # True if this tool produces the final answer


# ---------------------------------------------------------------------------
# Tool definitions (schemas only — execution is injected at runtime)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_logs",
        "description": (
            "Search log entries for a service. Returns matching log messages. "
            "Use this first to understand what errors are occurring."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "The service name to search logs for.",
                },
                "keyword_filter": {
                    "type": "string",
                    "description": "Optional keyword to filter logs (e.g., 'ERROR', 'timeout').",
                },
            },
            "required": ["service_name"],
        },
    },
    {
        "name": "detect_signals",
        "description": (
            "Run the rule engine on log entries to detect known incident patterns "
            "(database_issue, timeout_issue, auth_issue, etc.). "
            "Returns the detected issue_type, severity, and matched evidence logs. "
            "Always call this after search_logs to classify the incident."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "retrieve_runbooks",
        "description": (
            "Retrieve relevant runbook documents for operational guidance. "
            "Returns chunks of runbook content with relevance scores. "
            "Call this when you have identified an issue_type and need remediation steps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query combining incident title, service, and issue type.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of runbook chunks to retrieve (default: 3).",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "retrieve_similar_incidents",
        "description": (
            "Search historical incidents for similar past cases. "
            "Returns similar incidents with root causes and resolutions. "
            "Use this to learn from past resolutions before forming hypotheses."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query combining incident title, service, and issue type.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of similar incidents to retrieve (default: 3).",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_diagnosis",
        "description": (
            "Generate the final structured diagnosis. This is the TERMINAL action. "
            "Call this ONLY after you have gathered enough evidence from logs, "
            "runbooks, and similar incidents. "
            "Output format: diagnosis_summary, root_cause_hypotheses, impact_scope, "
            "suggested_actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def get_tool_schemas_text() -> str:
    """Return tool schemas as a formatted string for the LLM prompt."""
    import json

    lines = []
    for tool in TOOL_SCHEMAS:
        lines.append(f"- {tool['name']}: {tool['description']}")
        lines.append(f"  Parameters: {json.dumps(tool['parameters'])}")
    return "\n".join(lines)
