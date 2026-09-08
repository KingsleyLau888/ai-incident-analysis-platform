"""Query rewriting for multi-perspective RAG retrieval.

Generates 2-3 alternative queries from incident context, each emphasizing
a different angle (symptom, service, dependency).  Results from all queries
are fused with RRF.

Two modes:
    - LLM-driven: uses a real LLM to rewrite queries (more diverse)
    - Template-driven: rule-based query variants (always available)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class RewrittenQueries:
    original: str
    variants: list[str]
    provider: str  # "llm" | "template"


# ---------------------------------------------------------------------------
# LLM-driven rewriting
# ---------------------------------------------------------------------------

REWRITE_SYSTEM_PROMPT = """You are a query rewriting assistant for an incident diagnosis system.
Given an incident title, service name, issue type, and evidence log snippets,
generate 3 alternative search queries that would help retrieve relevant runbooks
and similar incidents.

Each query should emphasize a different perspective:
1. Symptom-focused: describe the observable error behavior
2. Service-focused: describe which service/component is affected
3. Root-cause-focused: describe the likely underlying cause

Return ONLY a JSON object (no markdown fences):
{"queries": ["query 1", "query 2", "query 3"]}"""


def _llm_rewrite(
    incident_title: str,
    service_name: str,
    issue_type: str,
    evidence_text: str,
) -> list[str] | None:
    """Try to rewrite queries with the configured LLM. Returns None on failure."""
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider != "openai_compatible":
        return None

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = os.getenv("LLM_MODEL", "")
    if not api_key or not base_url or not model:
        return None

    user_content = json.dumps(
        {
            "incident_title": incident_title,
            "service_name": service_name,
            "issue_type": issue_type,
            "evidence_logs": evidence_text[:500],
        }
    )

    try:
        import httpx

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content).get("queries", [])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Template-driven rewriting (always available)
# ---------------------------------------------------------------------------


# 证据关键词提取时跳过的高频泛词（不区分故障类型，浪费变体槽位）
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "with",
    "from", "to", "of", "in", "on", "at", "by", "as", "is", "are", "was",
    "were", "be", "been", "being", "this", "that", "these", "those", "it",
    "its", "not", "no", "has", "have", "had", "will", "would", "can", "could",
    "should", "may", "might", "do", "does", "did", "get", "got", "error",
    "failed", "failure", "fail", "unable", "cannot", "trying", "attempt",
    "attempts", "attempting", "while", "after", "during", "request", "requests",
    "response", "responses", "retry", "retries", "check", "service", "services",
    "using", "use", "used", "due", "caused", "cause", "occurred", "message",
    "log", "logs", "level", "status",
}


def _template_rewrite(
    incident_title: str,
    service_name: str,
    issue_type: str,
    evidence_text: str,
) -> list[str]:
    """Generate query variants using templates based on issue type."""
    issue_label = issue_type.replace("_", " ")
    evidence_excerpt = " ".join(dict.fromkeys(evidence_text.split()))[:200]
    variants = [
        # Symptom perspective：标题 + 服务 + 证据摘录
        f"{incident_title} {service_name} error symptoms {evidence_excerpt}",
    ]
    if evidence_text:
        keywords = _extract_keywords(evidence_text, 8)
        if keywords:
            variants.append(f"{service_name} {' '.join(keywords)} {issue_label}")
    if issue_type != "unknown":
        variants.append(f"{issue_label} troubleshooting {service_name}")
    # Ensure we have at least 2 variants
    if len(variants) < 2:
        variants.append(f"{incident_title} {service_name}")
    return variants


def _extract_keywords(text: str, max_words: int = 8) -> list[str]:
    """Extract salient words from evidence text.

    旧实现只匹配大写开头/下划线词，全小写的证据词（provider、refused、
    unavailable 等）被整体丢弃。改为按非字母数字切分、过滤停用词、去重取前 N 个。
    """
    import re

    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_./-]*", text)
    seen = set()
    result = []
    for word in words:
        lowered = word.lower()
        if len(lowered) < 3 or lowered in _STOPWORDS or lowered in seen:
            continue
        seen.add(lowered)
        result.append(lowered)
        if len(result) >= max_words:
            break
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def rewrite_query(
    incident_title: str,
    service_name: str,
    issue_type: str,
    evidence_text: str,
) -> RewrittenQueries:
    """Generate query variants for multi-perspective retrieval.

    Tries LLM rewriting first; falls back to templates.
    """
    original = " ".join(
        part for part in [incident_title, service_name, issue_type, evidence_text[:200]] if part
    )

    llm_variants = _llm_rewrite(
        incident_title=incident_title,
        service_name=service_name,
        issue_type=issue_type,
        evidence_text=evidence_text,
    )
    if llm_variants:
        return RewrittenQueries(
            original=original,
            variants=llm_variants,
            provider="llm",
        )

    template_variants = _template_rewrite(
        incident_title=incident_title,
        service_name=service_name,
        issue_type=issue_type,
        evidence_text=evidence_text,
    )
    return RewrittenQueries(
        original=original,
        variants=template_variants,
        provider="template",
    )
