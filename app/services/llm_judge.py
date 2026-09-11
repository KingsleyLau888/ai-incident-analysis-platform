"""LLM-as-Judge: evaluate diagnosis quality beyond surface-level keyword matching.

Provides four evaluation dimensions that complement rule-based metrics:
- diagnosis_coherence: is the reasoning chain logical and self-consistent?
- evidence_grounding: are conclusions supported by the provided evidence?
- hallucination_flag: does the diagnosis reference facts not in the evidence?
- actionability: are the suggested actions concrete and executable?
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Judgment result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JudgeVerdict:
    diagnosis_coherence: float  # 0.0 - 1.0
    evidence_grounding: float  # 0.0 - 1.0
    hallucination_flag: bool  # True = hallucination suspected
    actionability: float  # 0.0 - 1.0
    critique: str  # free-text explanation
    provider: str  # "llm" | "mock" | "unavailable"


# ---------------------------------------------------------------------------
# Judge prompt templates
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator of AI-generated incident diagnosis reports.
Your job is to score the diagnosis on four dimensions.  Be strict but fair.

IMPORTANT CONTEXT RULE: The diagnosis model was given TWO kinds of input:
1. evidence_logs — the raw runtime logs for this incident.
2. reference_materials — retrieved runbook chunks and similar historical incidents
   from a knowledge base (this is an open-book exam: these materials were
   legitimately given to the model as retrieval context).
Facts drawn from reference_materials are NOT hallucination. A citation of a runbook
source (e.g. "postgres_primary_unavailable.md") or a historical incident ID (e.g.
"HIST-TIMEOUT-001") that appears in reference_materials is legitimate grounding.
Hallucination means inventing facts present in NEITHER evidence_logs NOR
reference_materials, or citing a reference ID that does not appear in either.

Return ONLY a valid JSON object matching this schema (no markdown fences, no extra text):
{
  "diagnosis_coherence": <float 0.0-1.0>,
  "evidence_grounding": <float 0.0-1.0>,
  "hallucination_flag": <bool>,
  "actionability": <float 0.0-1.0>,
  "critique": "<2-3 sentence explanation>"
}

SCORING GUIDE:
- diagnosis_coherence: Does the diagnosis logically connect the incident, issue_type, and evidence?
  1.0 = perfectly coherent chain of reasoning; 0.0 = nonsensical or contradictory.

- evidence_grounding: Are the root cause hypotheses anchored to the evidence_logs AND/OR reference_materials?
  1.0 = every claim cites specific evidence or reference materials; 0.0 = claims unsupported or fabricated.

- hallucination_flag: Does the diagnosis mention services, errors, or facts NOT present in the
  evidence_logs AND NOT present in the reference_materials?
  true = hallucination or fabrication detected; false = consistent with provided inputs.

- actionability: Are the suggested actions specific and executable?
  1.0 = concrete commands/checks; 0.0 = vague advice like "investigate further".
"""


def build_judge_user_prompt(
    incident_title: str,
    service_name: str,
    issue_type: str,
    severity: str,
    evidence_messages: list[str],
    diagnosis_summary: str,
    root_cause_hypotheses: list[dict],
    suggested_actions: list[str],
    impact_scope: str,
    retrieved_runbook_chunks: list[dict] | None = None,
    similar_incidents: list[dict] | None = None,
) -> str:
    """Construct the evaluation payload for the judge LLM.

    F10/F12：裁判必须拿到与诊断模型相同的开卷资料（检索到的手册 chunk
    与相似事故），否则会把合法检索引用误判为幻觉。
    """
    payload: dict[str, Any] = {
        "incident_title": incident_title,
        "service_name": service_name,
        "issue_type": issue_type,
        "severity": severity,
        "evidence_logs": evidence_messages,
        "reference_materials": {
            "retrieved_runbook_chunks": retrieved_runbook_chunks or [],
            "similar_incidents": similar_incidents or [],
        },
        "diagnosis_to_evaluate": {
            "diagnosis_summary": diagnosis_summary,
            "root_cause_hypotheses": root_cause_hypotheses,
            "impact_scope": impact_scope,
            "suggested_actions": suggested_actions,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Judge implementations
# ---------------------------------------------------------------------------


class MockJudge:
    """Deterministic fallback judge — uses heuristics instead of an LLM."""

    def evaluate(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_messages: list[str],
        diagnosis_summary: str,
        root_cause_hypotheses: list[dict],
        suggested_actions: list[str],
        impact_scope: str,
        retrieved_runbook_chunks: list[dict] | None = None,
        similar_incidents: list[dict] | None = None,
    ) -> JudgeVerdict:
        # Heuristic scoring — not as nuanced as LLM but better than nothing.
        # F10/F12：启发式判断同样纳入开卷资料（检索手册 + 相似事故），
        # 只存在于参考资料中的名称不算幻觉。
        known_text = _known_facts_text(
            evidence_messages, retrieved_runbook_chunks, similar_incidents
        )
        coherence = _heuristic_coherence(issue_type, diagnosis_summary)
        grounding = _heuristic_grounding(known_text, root_cause_hypotheses)
        hallucination = _heuristic_hallucination(
            known_text, diagnosis_summary, root_cause_hypotheses, impact_scope
        )
        actionability = _heuristic_actionability(suggested_actions)
        return JudgeVerdict(
            diagnosis_coherence=coherence,
            evidence_grounding=grounding,
            hallucination_flag=hallucination,
            actionability=actionability,
            critique="Heuristic evaluation (no LLM available). Scores are approximate.",
            provider="mock",
        )


class LLMJudge:
    """Judge backed by a real OpenAI-compatible LLM."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        import httpx

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.http_client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def evaluate(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_messages: list[str],
        diagnosis_summary: str,
        root_cause_hypotheses: list[dict],
        suggested_actions: list[str],
        impact_scope: str,
        retrieved_runbook_chunks: list[dict] | None = None,
        similar_incidents: list[dict] | None = None,
    ) -> JudgeVerdict:
        user_content = build_judge_user_prompt(
            incident_title=incident_title,
            service_name=service_name,
            issue_type=issue_type,
            severity=severity,
            evidence_messages=evidence_messages,
            diagnosis_summary=diagnosis_summary,
            root_cause_hypotheses=root_cause_hypotheses,
            suggested_actions=list(suggested_actions),
            impact_scope=impact_scope,
            retrieved_runbook_chunks=retrieved_runbook_chunks,
            similar_incidents=similar_incidents,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = self.http_client.post("chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        scores = json.loads(content)
        return JudgeVerdict(
            diagnosis_coherence=float(scores.get("diagnosis_coherence", 0.5)),
            evidence_grounding=float(scores.get("evidence_grounding", 0.5)),
            hallucination_flag=bool(scores.get("hallucination_flag", False)),
            actionability=float(scores.get("actionability", 0.5)),
            critique=str(scores.get("critique", "No critique provided.")),
            provider="llm",
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_judge() -> MockJudge | LLMJudge:
    """Return a judge — LLM-backed if configured, otherwise heuristic."""
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider != "openai_compatible":
        return MockJudge()

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = os.getenv("LLM_MODEL", "")
    if not api_key or not base_url or not model:
        return MockJudge()

    try:
        return LLMJudge(api_key=api_key, base_url=base_url, model=model)
    except Exception:
        return MockJudge()


# ---------------------------------------------------------------------------
# Heuristic scoring helpers (used by MockJudge)
# ---------------------------------------------------------------------------


def _known_facts_text(
    evidence_messages: list[str],
    retrieved_runbook_chunks: list[dict] | None,
    similar_incidents: list[dict] | None,
) -> str:
    """合并裁判已知的全部材料文本：证据日志 + 检索手册 + 相似事故（F10/F12）。"""
    parts: list[str] = list(evidence_messages)
    for chunk in retrieved_runbook_chunks or []:
        parts.extend(str(value) for value in (chunk.get("source"), chunk.get("title"), chunk.get("content")) if value)
    for incident in similar_incidents or []:
        parts.extend(
            str(value)
            for value in (
                incident.get("historical_id"),
                incident.get("title"),
                incident.get("root_cause"),
                incident.get("resolution"),
            )
            if value
        )
    return " ".join(parts).lower()


def _heuristic_coherence(issue_type: str, diagnosis_summary: str) -> float:
    """Check if diagnosis mentions the issue type."""
    score = 0.5
    issue_label = issue_type.replace("_", " ")
    if issue_label.lower() in diagnosis_summary.lower():
        score += 0.3
    # Bonus for structured language
    if any(
        phrase in diagnosis_summary.lower()
        for phrase in ["showing signs of", "likely", "may be", "based on"]
    ):
        score += 0.2
    return min(score, 1.0)


def _heuristic_grounding(
    known_text: str, root_cause_hypotheses: list[dict]
) -> float:
    """Check if hypotheses reference known material keywords (evidence + references)."""
    if not known_text or not root_cause_hypotheses:
        return 0.3
    grounding_count = 0
    for hypothesis in root_cause_hypotheses:
        supporting = hypothesis.get("supporting_evidence", [])
        for item in supporting:
            # Check if evidence snippet appears in known materials
            if any(word.lower() in known_text for word in item.split()[:3]):
                grounding_count += 1
                break
    if not root_cause_hypotheses:
        return 0.3
    ratio = grounding_count / len(root_cause_hypotheses)
    return min(0.4 + ratio * 0.6, 1.0)


def _heuristic_hallucination(
    known_text: str,
    diagnosis_summary: str,
    root_cause_hypotheses: list[dict],
    impact_scope: str,
) -> bool:
    """Flag if the diagnosis mentions services/errors not in any known material."""
    evidence_text = known_text
    # Collect all service/entity mentions from the diagnosis
    all_diagnosis_text = diagnosis_summary + " " + impact_scope
    for h in root_cause_hypotheses:
        all_diagnosis_text += " " + h.get("cause", "")
    # Look for suspicious proper nouns (CapitalizedCompound words) not in evidence
    import re

    proper_nouns = set(re.findall(r"[A-Z][a-z]+(?:[A-Z][a-z]+)+", all_diagnosis_text))
    for noun in proper_nouns:
        if noun.lower() not in evidence_text:
            return True
    return False


def _heuristic_actionability(suggested_actions: list[str]) -> float:
    """Score based on specificity of actions."""
    if not suggested_actions:
        return 0.2
    score = 0.0
    for action in suggested_actions:
        # Concrete actions tend to start with verbs and mention specific targets
        action_lower = action.lower()
        if any(
            verb in action_lower
            for verb in ["check", "review", "investigate", "rollback", "restart", "increase"]
        ):
            score += 0.3
        if any(
            target in action_lower
            for target in ["connection", "pool", "database", "log", "config", "memory", "cache"]
        ):
            score += 0.2
    return min(score / max(len(suggested_actions), 1), 1.0)
