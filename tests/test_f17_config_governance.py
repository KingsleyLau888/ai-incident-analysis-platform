"""F17：统一配置校验与 .env 加载。

覆盖：默认配置合法、枚举/整数/浮点非法取值报错、openai_compatible 三件套校验、
错误信息不包含密钥值、prepare_config 坏配置抛 RuntimeError、.env 加载不覆盖已有变量。
"""

import pytest

from app.config import (
    load_dotenv_config,
    prepare_config,
    validate_startup_config,
)


def test_default_configuration_is_valid(monkeypatch):
    for name in (
        "LLM_PROVIDER", "RETRIEVAL_MODE", "CHUNKING_STRATEGY", "ANALYSIS_MODE",
        "RUNBOOK_FILTER_MODE", "AUTO_INCIDENT_ENABLED", "REACT_AGENT_ENABLED",
        "RUNBOOK_METADATA_FILTER", "CROSS_ENCODER_ENABLED",
        "AUTO_INCIDENT_ERROR_THRESHOLD", "AUTO_INCIDENT_WINDOW_SECONDS",
        "AUTO_INCIDENT_DEDUPE_MINUTES", "ANALYSIS_LOG_WINDOW_MINUTES",
        "PIPELINE_VARIANT_TOP_K", "RRF_K", "VECTOR_RETRIEVAL_CANDIDATES",
        "MAX_REQUEST_BODY_BYTES", "WRITE_RATE_LIMIT_PER_MINUTE",
        "RUNBOOK_QUERY_EVIDENCE_MAX_CHARS", "RUNBOOK_FILTER_SOFT_PENALTY",
        "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    assert validate_startup_config() == []


def test_invalid_enum_values_are_reported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "banana")
    monkeypatch.setenv("RETRIEVAL_MODE", "banana")
    problems = validate_startup_config()
    assert any("LLM_PROVIDER" in problem for problem in problems)
    assert any("RETRIEVAL_MODE" in problem for problem in problems)


def test_invalid_int_and_float_values_are_reported(monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "abc")
    monkeypatch.setenv("AUTO_INCIDENT_WINDOW_SECONDS", "0")
    monkeypatch.setenv("RUNBOOK_FILTER_SOFT_PENALTY", "1.5")
    problems = validate_startup_config()
    assert any("AUTO_INCIDENT_ERROR_THRESHOLD" in problem for problem in problems)
    assert any("AUTO_INCIDENT_WINDOW_SECONDS" in problem for problem in problems)
    assert any("RUNBOOK_FILTER_SOFT_PENALTY" in problem for problem in problems)


def test_valid_custom_values_pass(monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "5")
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "0")  # 0 = 不限
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "0")
    assert validate_startup_config() == []


def test_openai_provider_requires_three_keys(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    problems = validate_startup_config()
    assert any("LLM_API_KEY" in problem for problem in problems)
    assert any("LLM_BASE_URL" in problem for problem in problems)
    assert any("LLM_MODEL" in problem for problem in problems)

    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "http://x")
    monkeypatch.setenv("LLM_MODEL", "m")
    assert validate_startup_config() == []


def test_validation_errors_do_not_contain_key_values(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-key-value")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    problems = validate_startup_config()
    assert problems
    for problem in problems:
        assert "super-secret-key-value" not in problem


def test_prepare_config_raises_on_bad_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "banana")
    with pytest.raises(RuntimeError, match="启动配置错误"):
        prepare_config()


def test_dotenv_loaded_without_overriding_existing(monkeypatch, tmp_path):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("AUTO_INCIDENT_WINDOW_SECONDS=90\n", encoding="utf-8")
    monkeypatch.delenv("AUTO_INCIDENT_WINDOW_SECONDS", raising=False)
    load_dotenv_config(paths=(dotenv_path,))
    assert validate_startup_config() == []  # 90 合法
    import os
    assert os.getenv("AUTO_INCIDENT_WINDOW_SECONDS") == "90"

    # 已存在的环境变量优先于 .env 文件
    monkeypatch.setenv("AUTO_INCIDENT_WINDOW_SECONDS", "42")
    load_dotenv_config(paths=(dotenv_path,))
    import os
    assert os.getenv("AUTO_INCIDENT_WINDOW_SECONDS") == "42"
