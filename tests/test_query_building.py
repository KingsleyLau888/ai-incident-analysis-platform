"""查询构建与过滤模式开关的回归测试（Step 3/4 改动）。

覆盖：build_runbook_query 的证据去重/截断/可读类型词；RUNBOOK_FILTER_MODE
环境解析；_extract_keywords 小写证据词提取与停用词过滤。
"""

import os
from types import SimpleNamespace

from app.services.query_rewriter import _extract_keywords
from app.services.runbook_retriever import (
    _runbook_filter_mode,
    build_runbook_query,
)


def _logs(*messages: str) -> list:
    return [SimpleNamespace(message=message) for message in messages]


# ── build_runbook_query ─────────────────────────────────────────────

def test_build_query_dedupes_repeated_evidence():
    query = build_runbook_query(
        incident_title="checkout down",
        service_name="order-service",
        evidence_logs=_logs("connection refused", "connection refused", "connection refused"),
        issue_type="database_issue",
    )
    # 同文案日志只出现一次，重复消息不会虚增查询词权重
    assert query.count("connection refused") == 1


def test_build_query_uses_human_readable_issue_label():
    query = build_runbook_query(
        incident_title="checkout down",
        service_name="order-service",
        evidence_logs=_logs("connection refused"),
        issue_type="database_issue",
    )
    # 语料中是 "database" 词，带下划线的 "database_issue" 是无效查询 token
    assert "database issue" in query
    assert "database_issue" not in query


def test_build_query_truncates_evidence(monkeypatch):
    monkeypatch.setenv("RUNBOOK_QUERY_EVIDENCE_MAX_CHARS", "20")
    query = build_runbook_query(
        incident_title="t",
        service_name="s",
        evidence_logs=_logs("a" * 100),
        issue_type="cache_issue",
    )
    assert "a" * 40 not in query


# ── 过滤模式解析 ────────────────────────────────────────────────────

def test_filter_mode_defaults_to_hard(monkeypatch):
    monkeypatch.delenv("RUNBOOK_FILTER_MODE", raising=False)
    monkeypatch.delenv("RUNBOOK_METADATA_FILTER", raising=False)
    assert _runbook_filter_mode() == "hard"


def test_filter_mode_invalid_falls_back_to_hard(monkeypatch):
    monkeypatch.setenv("RUNBOOK_FILTER_MODE", "banana")
    assert _runbook_filter_mode() == "hard"


def test_filter_mode_soft(monkeypatch):
    monkeypatch.setenv("RUNBOOK_FILTER_MODE", "soft")
    assert _runbook_filter_mode() == "soft"


def test_filter_mode_metadata_off_forces_off(monkeypatch):
    monkeypatch.setenv("RUNBOOK_METADATA_FILTER", "0")
    monkeypatch.setenv("RUNBOOK_FILTER_MODE", "soft")
    assert _runbook_filter_mode() == "off"


# ── 关键词提取 ──────────────────────────────────────────────────────

def test_extract_keywords_keeps_lowercase_evidence_words():
    # 旧实现只匹配大写开头词，全小写证据词被整体丢弃
    keywords = _extract_keywords(
        "ERROR payment provider request timed out after dns retry", max_words=8
    )
    assert "provider" in keywords
    assert "dns" in keywords
    assert "payment" in keywords


def test_extract_keywords_filters_stopwords():
    keywords = _extract_keywords(
        "the request failed with timeout after waiting for the worker", max_words=10
    )
    assert "the" not in keywords
    assert "failed" not in keywords
    assert "timeout" in keywords
    assert "worker" in keywords


def test_extract_keywords_dedupes(monkeypatch):
    keywords = _extract_keywords("queue lag queue lag queue lag", max_words=8)
    assert keywords.count("queue") == 1
    assert keywords.count("lag") == 1
