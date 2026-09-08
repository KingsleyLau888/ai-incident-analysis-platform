"""infer_issue_type 计分制的回归测试。

背景：旧实现按类别顺序优先，"identity provider" 中的 "provider" 会把
token_signing_key_rotation 的 chunk 误标成 timeout_issue，污染硬过滤候选池。
计分制按类别关键词命中次数取最高，平票按类别表顺序。
"""

from collections import Counter

from app.services.runbook_chunker import infer_issue_type, load_runbook_chunks


# ── 纯函数级：修复目标场景 ──────────────────────────────────────────

def test_identity_provider_chunk_stays_auth():
    """"provider" 命中 timeout 一次，auth/token 命中更多 → auth_issue。"""
    result = infer_issue_type(
        source="token_signing_key_rotation.md",
        title="Common Signals",
        content="invalid signature, unknown kid, JWT validation failed. "
        "Auth failures after identity provider key rotation. "
        "Some services reject tokens while others accept.",
    )
    assert result == "auth_issue"


def test_secret_mismatch_causes_chunk_stays_auth():
    """正文提到 database 但主题是 secret/credential → auth_issue。"""
    result = infer_issue_type(
        source="config_secret_mismatch.md",
        title="Likely Causes",
        content="Old pods still use previous secret values. "
        "Database password changed but ConfigMap/Secret was not refreshed.",
    )
    assert result == "auth_issue"


def test_payment_provider_timeout_stays_timeout():
    """"payment provider" 场景不能被计分制误伤成 auth。"""
    result = infer_issue_type(
        source="payment_provider_timeout.md",
        title="Likely Causes",
        content="Payment provider gateway timeout while calling the payment API. "
        "Provider deadline exceeded and retry exhausted.",
    )
    assert result == "timeout_issue"


def test_no_keyword_returns_unknown():
    assert infer_issue_type("misc.md", "Notes", "nothing suspicious here") == "unknown"


# ── 文件级：整本手册标注不回退 ──────────────────────────────────────

def _file_label_distribution(source: str) -> Counter:
    chunks = [c for c in load_runbook_chunks() if c.source == source]
    assert chunks, f"runbook not found: {source}"
    return Counter(c.issue_type for c in chunks)


def test_token_signing_key_rotation_all_auth():
    dist = _file_label_distribution("token_signing_key_rotation.md")
    assert dist["auth_issue"] == len(list(dist.elements()))
    assert "timeout_issue" not in dist


def test_config_secret_mismatch_all_auth():
    dist = _file_label_distribution("config_secret_mismatch.md")
    assert dist["auth_issue"] == len(list(dist.elements()))
    assert "database_issue" not in dist


def test_cache_stampede_all_cache():
    dist = _file_label_distribution("cache_stampede.md")
    assert dist["cache_issue"] == len(list(dist.elements()))


def test_payment_provider_timeout_all_timeout():
    dist = _file_label_distribution("payment_provider_timeout.md")
    assert dist["timeout_issue"] == len(list(dist.elements()))


def test_core_runbooks_keep_majority_label():
    for source, expected in [
        ("database_issue.md", "database_issue"),
        ("timeout_issue.md", "timeout_issue"),
        ("memory_issue.md", "memory_issue"),
        ("mysql_connection_pool.md", "database_issue"),
        ("kafka_consumer_rebalance.md", "timeout_issue"),
        ("message_queue_lag.md", "timeout_issue"),
    ]:
        dist = _file_label_distribution(source)
        assert dist.most_common(1)[0][0] == expected, f"{source}: {dist}"
