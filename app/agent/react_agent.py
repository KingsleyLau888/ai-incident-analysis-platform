"""ReAct (Reasoning + Acting) agent for incident diagnosis.

The agent follows the ReAct pattern:
    1. Observe: receive incident context (title, service, logs)
    2. Think: decide which tool to call next
    3. Act: execute the tool
    4. Observe: incorporate the tool result
    Repeat until the agent calls the terminal 'generate_diagnosis' tool
    or reaches the maximum step limit.

Two modes:
    - LLM-driven: uses a real LLM to decide Thought/Action at each step
    - Deterministic: follows a fixed workflow (matches old Pipeline behavior)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from app.agent.tools import TOOL_SCHEMAS, get_tool_schemas_text
from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident

# F05：代码级门禁（不再只靠提示词）
_KNOWN_TOOLS = {tool["name"] for tool in TOOL_SCHEMAS}
_REQUIRED_EVIDENCE_TOOLS = ("search_logs", "detect_signals")


class _ToolInputError(ValueError):
    """工具参数非法（强类型与限额）：作为决策错误显式返回，不吞成泛化失败。"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AgentStep:
    step_number: int
    thought: str
    action: str | None  # tool name, or None for final answer
    action_input: dict[str, Any] | None
    observation: str
    is_final: bool = False


@dataclass
class AgentResult:
    steps: list[AgentStep]
    final_diagnosis: Any | None
    provider: str  # "react_llm" | "react_deterministic"
    final_context: dict[str, Any] = field(default_factory=dict)
    # F05：证据不足时不给诊断（不用 MAX_STEPS 掩盖零取证）
    insufficient_evidence: bool = False


# ---------------------------------------------------------------------------
# ReAct prompt templates
# ---------------------------------------------------------------------------

REACT_SYSTEM_PROMPT = """You are an incident diagnosis agent. Your job is to investigate an incident
step-by-step using the available tools, then produce a structured diagnosis.

Follow the ReAct (Reasoning + Acting) pattern:
1. Think about what you need to know next
2. Choose ONE tool to call
3. Observe the result
4. Repeat until you have enough information

When you are ready to produce the final diagnosis, call `generate_diagnosis`.

RULES:
- Start by searching logs to understand the incident.
- Always detect signals after searching logs.
- Retrieve runbooks and similar incidents to ground your diagnosis.
- Use focused investigation tools when the first signals are ambiguous:
  query_logs_by_keyword, summarize_timeline, compare_log_level_trend,
  inspect_dependency_signals.
- Do NOT call the same tool twice with identical parameters.
- Call `generate_diagnosis` only when you have gathered sufficient evidence."""


def build_react_user_prompt(
    incident_title: str,
    service_name: str,
    issue_type: str | None,
    severity: str | None,
    evidence_logs: list[LogEntry] | None,
    retrieved_runbook_chunks: list[RetrievedRunbookChunk] | None,
    similar_incidents: list[SimilarIncident] | None,
    current_step: int,
    max_steps: int,
    history: list[dict[str, Any]],
) -> str:
    """Build the user prompt for the current ReAct step."""
    tool_text = get_tool_schemas_text()

    evidence_text = ""
    if evidence_logs:
        evidence_text = "\n".join(
            f"  [{log.level}] {log.message}" for log in evidence_logs[:10]
        )

    runbook_text = ""
    if retrieved_runbook_chunks:
        runbook_text = "\n".join(
            f"  [{chunk.score:.3f}] {chunk.title}: {chunk.content[:200]}"
            for chunk in retrieved_runbook_chunks[:3]
        )

    incident_text = ""
    if similar_incidents:
        incident_text = "\n".join(
            f"  [{inc.similarity_score:.3f}] {inc.title} → {inc.root_cause}"
            for inc in similar_incidents[:3]
        )

    history_text = ""
    if history:
        history_lines = []
        for entry in history:
            history_lines.append(f"Step {entry['step']}:")
            history_lines.append(f"  Thought: {entry['thought']}")
            history_lines.append(f"  Action: {entry['action']}")
            history_lines.append(f"  Observation: {entry['observation'][:300]}")
        history_text = "\n".join(history_lines)

    notes_text = ""
    notes = history[-5:] if history else []
    if notes:
        notes_text = "\n".join(
            f"  {entry['action']}: {entry['observation'][:220]}" for entry in notes
        )

    return f"""## Incident Context

Title: {incident_title}
Service: {service_name}
Issue Type (preliminary): {issue_type or 'unknown'}
Severity (preliminary): {severity or 'unknown'}

## Available Evidence Logs
{evidence_text or '(none yet — use search_logs to find logs)'}

## Retrieved Runbook Chunks
{runbook_text or '(none yet — use retrieve_runbooks)'}

## Similar Historical Incidents
{incident_text or '(none yet — use retrieve_similar_incidents)'}

## Available Tools
{tool_text}

## Step History
{history_text or '(start of investigation)'}

## Recent Tool Observations
{notes_text or '(none yet)'}

## Current Status
You are at step {current_step} of {max_steps}.

Respond in this EXACT JSON format (no markdown fences):
{{
  "thought": "<your reasoning about what to do next>",
  "action": "<tool name or 'generate_diagnosis' if ready>",
  "action_input": {{<parameters for the tool, or empty object for generate_diagnosis>}}
}}

If you have enough information to diagnose, set action to "generate_diagnosis".
Otherwise, choose the next most useful tool."""


# ===================================================================
# ReAct Agent
# ===================================================================


class ReActAgent:
    """ReAct agent that iteratively investigates an incident.

    When *llm_client* is provided, the agent uses the LLM to decide
    each Thought/Action.  Otherwise it follows a deterministic workflow
    that mirrors the old Pipeline behavior.
    """

    MAX_STEPS = 5

    def __init__(
        self,
        llm_client: object | None = None,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self._llm = llm_client
        self._max_steps = max_steps

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def investigate(
        self,
        incident_title: str,
        service_name: str,
        # Tool executors (injected by the analysis service)
        search_logs_fn,
        detect_signals_fn,
        retrieve_runbooks_fn,
        retrieve_similar_incidents_fn,
        generate_diagnosis_fn,
    ) -> AgentResult:
        """Run the ReAct investigation loop and return AgentResult."""

        # Mutable context that tools update
        ctx: dict[str, Any] = {
            "logs": [],
            "evidence_logs": [],
            "issue_type": None,
            "severity": None,
            "runbook_chunks": [],
            "similar_incidents": [],
            "investigation_notes": [],
            "keyword_matches": [],
            # F05：代码记录成功执行状态（可序列化为列表，避免 set 进入结果上下文）
            "successful_tools": [],
        }

        steps: list[AgentStep] = []
        history: list[dict[str, Any]] = []
        seen_calls: set[tuple[str, str]] = set()

        for step_num in range(1, self._max_steps + 1):
            if self._llm is not None:
                thought, action_name, action_input = self._llm_decide(
                    incident_title=incident_title,
                    service_name=service_name,
                    ctx=ctx,
                    step_num=step_num,
                    history=history,
                )
            else:
                thought, action_name, action_input = self._deterministic_decide(
                    ctx=ctx,
                    step_num=step_num,
                )

            # F05：未知工具是决策错误，不再静默转成 generate_diagnosis
            if action_name not in _KNOWN_TOOLS:
                step = AgentStep(
                    step_number=step_num,
                    thought=thought,
                    action=action_name,
                    action_input=action_input,
                    observation=(
                        f"Decision error: unknown tool {action_name!r}. "
                        "Choose one of the available tools."
                    ),
                )
                steps.append(step)
                history.append(
                    {
                        "step": step_num,
                        "thought": thought,
                        "action": action_name,
                        "observation": step.observation,
                    }
                )
                continue

            if action_name == "generate_diagnosis":
                # F05：诊断前置条件——必须完成过取证（search_logs + detect_signals）
                if not self._has_sufficient_evidence(ctx):
                    message = (
                        "Decision error: generate_diagnosis requires successful "
                        "search_logs and detect_signals first. Continue investigating."
                    )
                    if step_num == self._max_steps:
                        return self._insufficient_evidence_result(
                            steps=steps,
                            ctx=ctx,
                            thought=thought,
                            message=message,
                        )
                    step = AgentStep(
                        step_number=step_num,
                        thought=thought,
                        action=action_name,
                        action_input={},
                        observation=message,
                    )
                    steps.append(step)
                    history.append(
                        {
                            "step": step_num,
                            "thought": thought,
                            "action": action_name,
                            "observation": step.observation,
                        }
                    )
                    continue
                diagnosis = generate_diagnosis_fn(ctx)
                steps.append(
                    AgentStep(
                        step_number=step_num,
                        thought=thought,
                        action="generate_diagnosis",
                        action_input={},
                        observation="Structured diagnosis generated.",
                        is_final=True,
                    )
                )
                return AgentResult(
                    steps=steps,
                    final_diagnosis=diagnosis,
                    final_context=dict(ctx),
                    provider="react_llm" if self._llm else "react_deterministic",
                )

            # F05：重复调用由代码拒绝（不再只靠提示词禁止）
            call_key = (action_name, json.dumps(action_input or {}, sort_keys=True))
            if call_key in seen_calls:
                step = AgentStep(
                    step_number=step_num,
                    thought=thought,
                    action=action_name,
                    action_input=action_input,
                    observation=(
                        f"Rejected duplicate tool call: {action_name} with "
                        f"{action_input or {}}."
                    ),
                )
                steps.append(step)
                history.append(
                    {
                        "step": step_num,
                        "thought": thought,
                        "action": action_name,
                        "observation": step.observation,
                    }
                )
                continue
            seen_calls.add(call_key)

            # Execute the chosen tool
            observation, ok = self._execute_tool(
                action_name=action_name,
                action_input=action_input or {},
                ctx=ctx,
                incident_title=incident_title,
                service_name=service_name,
                search_logs_fn=search_logs_fn,
                detect_signals_fn=detect_signals_fn,
                retrieve_runbooks_fn=retrieve_runbooks_fn,
                retrieve_similar_incidents_fn=retrieve_similar_incidents_fn,
            )
            if ok:
                ctx["successful_tools"].append(action_name)

            step = AgentStep(
                step_number=step_num,
                thought=thought,
                action=action_name,
                action_input=action_input,
                observation=observation,
            )
            steps.append(step)
            history.append(
                {
                    "step": step_num,
                    "thought": thought,
                    "action": action_name,
                    "observation": observation,
                }
            )

        # 预算耗尽：证据齐全才强制出诊断；否则如实返回证据不足（F05）
        if self._has_sufficient_evidence(ctx):
            diagnosis = generate_diagnosis_fn(ctx)
            steps.append(
                AgentStep(
                    step_number=self._max_steps,
                    thought="Reached maximum steps. Generating diagnosis with available information.",
                    action="generate_diagnosis",
                    action_input={},
                    observation="Structured diagnosis generated.",
                    is_final=True,
                )
            )
            return AgentResult(
                steps=steps,
                final_diagnosis=diagnosis,
                final_context=dict(ctx),
                provider="react_llm" if self._llm else "react_deterministic",
            )
        return self._insufficient_evidence_result(
            steps=steps,
            ctx=ctx,
            thought="Reached maximum steps without sufficient evidence.",
            message="Budget exhausted without successful search_logs and detect_signals.",
        )

    # ------------------------------------------------------------------
    # Evidence gating helpers (F05)
    # ------------------------------------------------------------------

    @staticmethod
    def _has_sufficient_evidence(ctx: dict[str, Any]) -> bool:
        return all(tool in ctx.get("successful_tools", []) for tool in _REQUIRED_EVIDENCE_TOOLS)

    def _insufficient_evidence_result(
        self,
        steps: list[AgentStep],
        ctx: dict[str, Any],
        thought: str,
        message: str,
    ) -> AgentResult:
        steps.append(
            AgentStep(
                step_number=steps[-1].step_number + 1 if steps else 1,
                thought=thought,
                action="generate_diagnosis",
                action_input={},
                observation=f"Insufficient evidence: {message}",
                is_final=True,
            )
        )
        return AgentResult(
            steps=steps,
            final_diagnosis=None,
            final_context=dict(ctx),
            provider="react_llm" if self._llm is not None else "react_deterministic",
            insufficient_evidence=True,
        )

    # ------------------------------------------------------------------
    # LLM-driven decision
    # ------------------------------------------------------------------

    def _llm_decide(
        self,
        incident_title: str,
        service_name: str,
        ctx: dict[str, Any],
        step_num: int,
        history: list[dict[str, Any]],
    ) -> tuple[str, str | None, dict[str, Any] | None]:
        """Ask the LLM to decide the next action."""
        user_prompt = build_react_user_prompt(
            incident_title=incident_title,
            service_name=service_name,
            issue_type=ctx.get("issue_type"),
            severity=ctx.get("severity"),
            evidence_logs=ctx.get("evidence_logs"),
            retrieved_runbook_chunks=ctx.get("runbook_chunks"),
            similar_incidents=ctx.get("similar_incidents"),
            current_step=step_num,
            max_steps=self._max_steps,
            history=history,
        )

        try:
            result = self._call_llm(user_prompt)
            thought = result.get("thought", "Proceeding to next step.")
            action = result.get("action", "")
            action_input = result.get("action_input", {})
            if not isinstance(action_input, dict):
                action_input = {}
            # F05：未知动作不再静默转 generate_diagnosis，交给主循环报决策错误
            return thought, action, action_input
        except Exception:
            # Fall back to deterministic on LLM error
            return self._deterministic_decide(ctx, step_num)

    def _call_llm(self, user_prompt: str) -> dict[str, Any]:
        """Call the LLM for a ReAct decision. Delegates to the injected client."""
        # The llm_client is expected to have a method:
        #   decide_action(system_prompt, user_prompt) -> dict
        if hasattr(self._llm, "decide_action"):
            return self._llm.decide_action(REACT_SYSTEM_PROMPT, user_prompt)

        # Generic fallback — use a raw chat completion
        import httpx

        payload = {
            "model": getattr(self._llm, "model", ""),
            "messages": [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {getattr(self._llm, 'api_key', '')}"}
        base_url = getattr(self._llm, "base_url", "")
        with httpx.Client(base_url=base_url, timeout=60.0) as client:
            response = client.post("chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)

    # ------------------------------------------------------------------
    # Deterministic decision (mock / fallback)
    # ------------------------------------------------------------------

    def _deterministic_decide(
        self,
        ctx: dict[str, Any],
        step_num: int,
    ) -> tuple[str, str, dict[str, Any] | None]:
        """Fixed workflow matching the old Pipeline behavior."""
        workflow = [
            (
                "I need to find relevant logs for this incident.",
                "search_logs",
                {"service_name": ""},
            ),
            (
                "I should detect signal patterns in the logs.",
                "detect_signals",
                {},
            ),
            (
                "I should retrieve relevant runbooks for operational guidance.",
                "retrieve_runbooks",
                {"query": "", "top_k": 3},
            ),
            (
                "I should check similar historical incidents for past resolutions.",
                "retrieve_similar_incidents",
                {"query": "", "top_k": 3},
            ),
            (
                "I have enough evidence. Generating structured diagnosis.",
                "generate_diagnosis",
                {},
            ),
        ]
        if step_num <= len(workflow):
            return workflow[step_num - 1]
        return (
            "All steps completed. Generating final diagnosis.",
            "generate_diagnosis",
            {},
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(
        self,
        action_name: str,
        action_input: dict[str, Any],
        ctx: dict[str, Any],
        incident_title: str,
        service_name: str,
        search_logs_fn,
        detect_signals_fn,
        retrieve_runbooks_fn,
        retrieve_similar_incidents_fn,
    ) -> tuple[str, bool]:
        """Dispatch tool execution and update context.

        返回 (observation, success)：只有真正执行成功才计入取证状态（F05）。
        参数非法（_ToolInputError）与异常都算失败，observation 说明原因。
        """
        try:
            if action_name == "search_logs":
                logs = search_logs_fn(ctx)
                ctx["logs"] = logs
                return f"Found {len(logs)} log entries.", True

            elif action_name == "detect_signals":
                result = detect_signals_fn(ctx)
                ctx["issue_type"] = result.get("issue_type")
                ctx["severity"] = result.get("severity")
                ctx["evidence_logs"] = result.get("evidence_logs", [])
                return (
                    f"Detected issue_type={result.get('issue_type')}, "
                    f"severity={result.get('severity')}, "
                    f"matched_issues={result.get('matched_issues', [])}, "
                    f"evidence_logs_count={len(result.get('evidence_logs', []))}",
                    True,
                )

            elif action_name == "retrieve_runbooks":
                query = action_input.get("query") or build_retrieval_query(
                    incident_title, service_name, ctx
                )
                top_k = _bounded_int(action_input, "top_k", default=3, minimum=1, maximum=20)
                chunks = retrieve_runbooks_fn(
                    query, top_k, issue_type=ctx.get("issue_type")
                )
                ctx["runbook_chunks"] = chunks
                sources = [c.source for c in chunks]
                return f"Retrieved {len(chunks)} runbook chunks: {', '.join(sources) or 'none'}.", True

            elif action_name == "query_logs_by_keyword":
                keyword = str(action_input.get("keyword", "")).strip()
                if not keyword:
                    raise _ToolInputError("keyword must be a non-empty string.")
                level = str(action_input.get("level", "")).strip().upper()
                top_k = _bounded_int(action_input, "top_k", default=5, minimum=1, maximum=50)
                logs = ctx.get("logs", [])
                matches = []
                for log in logs:
                    message = getattr(log, "message", "")
                    log_level = getattr(log, "level", "")
                    if keyword.lower() not in message.lower():
                        continue
                    if level and log_level.upper() != level:
                        continue
                    matches.append(log)
                # F06：匹配日志按 log id 去重后进入最终证据（可回溯来源）
                known_ids = {getattr(log, "id", None) for log in ctx.get("keyword_matches", [])}
                ctx.setdefault("keyword_matches", []).extend(
                    log for log in matches if getattr(log, "id", None) not in known_ids
                )
                ctx.setdefault("investigation_notes", []).append(
                    f"Keyword search `{keyword}` matched {len(matches)} logs "
                    f"(ids: {[getattr(log, 'id', None) for log in matches[:top_k]]})."
                )
                preview = "; ".join(getattr(log, "message", "") for log in matches[:top_k])
                return (
                    f"Keyword `{keyword}` matched {len(matches)} logs"
                    + (f": {preview}" if preview else "."),
                    True,
                )

            elif action_name == "summarize_timeline":
                limit = _bounded_int(action_input, "limit", default=8, minimum=1, maximum=50)
                logs = ctx.get("logs", [])
                selected = logs[:limit]
                timeline = [
                    f"{getattr(log, 'timestamp', '')} {getattr(log, 'level', '')}: {getattr(log, 'message', '')}"
                    for log in selected
                ]
                note = f"Timeline built with {len(selected)} of {len(logs)} logs."
                ctx.setdefault("investigation_notes", []).append(note)
                return note + (" " + " | ".join(timeline) if timeline else ""), True

            elif action_name == "compare_log_level_trend":
                logs = ctx.get("logs", [])
                midpoint = len(logs) // 2
                first_half = logs[:midpoint]
                second_half = logs[midpoint:]
                first_counts = _level_counts(first_half)
                second_counts = _level_counts(second_half)
                first_errors = first_counts.get("ERROR", 0) + first_counts.get("CRITICAL", 0)
                second_errors = second_counts.get("ERROR", 0) + second_counts.get("CRITICAL", 0)
                direction = "increased" if second_errors > first_errors else "not increased"
                observation = (
                    f"Error trend {direction}: first_half_errors={first_errors}, "
                    f"second_half_errors={second_errors}, first_counts={first_counts}, "
                    f"second_counts={second_counts}."
                )
                ctx.setdefault("investigation_notes", []).append(observation)
                return observation, True

            elif action_name == "inspect_dependency_signals":
                dependency_terms = [
                    "mysql", "postgres", "database", "dbconnection", "redis",
                    "cache", "auth", "token", "payment-provider", "upstream",
                    "connection pool", "shop-primary", "mysql-primary",
                ]
                logs = ctx.get("logs", [])
                counts = {}
                for term in dependency_terms:
                    count = sum(
                        1 for log in logs
                        if term.lower() in getattr(log, "message", "").lower()
                    )
                    if count:
                        counts[term] = count
                observation = (
                    f"Dependency signals found: {counts}."
                    if counts else "No known dependency signals found in logs."
                )
                ctx.setdefault("investigation_notes", []).append(observation)
                return observation, True

            elif action_name == "retrieve_similar_incidents":
                query = action_input.get("query") or build_retrieval_query(
                    incident_title, service_name, ctx
                )
                top_k = _bounded_int(action_input, "top_k", default=3, minimum=1, maximum=20)
                incidents = retrieve_similar_incidents_fn(
                    query, top_k, issue_type=ctx.get("issue_type")
                )
                ctx["similar_incidents"] = incidents
                titles = [inc.title for inc in incidents]
                return f"Retrieved {len(incidents)} similar incidents: {', '.join(titles) or 'none'}.", True

            else:
                return f"Unknown tool: {action_name}", False

        except _ToolInputError as exc:
            return f"Tool {action_name} rejected invalid input: {exc}", False
        except Exception as exc:
            return f"Tool {action_name} failed: {exc}", False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_retrieval_query(
    incident_title: str,
    service_name: str,
    ctx: dict[str, Any],
) -> str:
    """Build a retrieval query from incident context."""
    evidence_text = " ".join(
        log.message if hasattr(log, "message") else str(log)
        for log in ctx.get("evidence_logs", [])[:5]
    )
    return " ".join(
        part
        for part in [
            incident_title,
            service_name,
            ctx.get("issue_type", ""),
            evidence_text,
        ]
        if part
    )


def _bounded_int(
    action_input: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """强类型参数限额（F05）：非整数或超界都报 _ToolInputError。"""
    raw = action_input.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise _ToolInputError(
            f"{key} must be an integer between {minimum} and {maximum}, got {raw!r}."
        ) from None
    if not (minimum <= value <= maximum):
        raise _ToolInputError(
            f"{key} must be between {minimum} and {maximum}, got {value}."
        )
    return value


def _level_counts(logs: list[LogEntry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for log in logs:
        level = getattr(log, "level", "UNKNOWN").upper()
        counts[level] = counts.get(level, 0) + 1
    return counts
