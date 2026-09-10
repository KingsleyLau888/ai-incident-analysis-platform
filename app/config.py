"""统一配置清单、.env 加载与启动校验（F17）。

三层约定：
- 启动配置：进程启动时由 `prepare_config()`（create_app 调用）加载并校验一次，
  非法取值启动即报错，不静默回退；错误信息只点名变量，绝不包含密钥值。
- 请求配置：如 AUTO_INCIDENT_*（检测阈值/窗口/去重分钟数）等热调参数，
  仍由各模块按请求读环境变量（保持现有行为），不在启动时校验。
- 测试隔离：conftest 不调用 prepare_config，测试不受本机 .env 影响。

配置读取本身仍走 os.getenv，本模块只做清单、加载与校验，不引入新读取路径。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── 启动配置清单 ─────────────────────────────────────────────────────────────

# 枚举取值：环境变量 → (合法取值集合, 默认值)
_ENUM_CONFIG: dict[str, tuple[set[str], str]] = {
    "LLM_PROVIDER": ({"mock", "openai_compatible"}, "mock"),
    "RETRIEVAL_MODE": ({"tfidf", "sentence-transformers", "hybrid", "chromadb"}, "tfidf"),
    "CHUNKING_STRATEGY": ({"markdown", "fixed", "semantic"}, "markdown"),
    "ANALYSIS_MODE": ({"auto", "pipeline", "agent"}, "auto"),
    "RUNBOOK_FILTER_MODE": ({"hard", "soft", "off"}, "hard"),
}

# 布尔取值：1/true/yes 为真，0/false/no 为假
_BOOL_CONFIG: tuple[str, ...] = (
    "AUTO_INCIDENT_ENABLED",
    "REACT_AGENT_ENABLED",
    "RUNBOOK_METADATA_FILTER",
    "CROSS_ENCODER_ENABLED",
)

# 整数取值：环境变量 → (默认值, 最小值, 最大值)；<=0 允许的项以 0 为下界表示"不限"
_INT_CONFIG: dict[str, tuple[int, int, int]] = {
    "AUTO_INCIDENT_ERROR_THRESHOLD": (3, 1, 1000),
    "AUTO_INCIDENT_WINDOW_SECONDS": (60, 1, 3600),
    "AUTO_INCIDENT_DEDUPE_MINUTES": (10, 1, 1440),
    "ANALYSIS_LOG_WINDOW_MINUTES": (5, 1, 1440),
    "PIPELINE_VARIANT_TOP_K": (5, 1, 100),
    "RRF_K": (60, 1, 1000),
    "VECTOR_RETRIEVAL_CANDIDATES": (10, 1, 1000),
    "MAX_REQUEST_BODY_BYTES": (1_000_000, 0, 10**9),
    "WRITE_RATE_LIMIT_PER_MINUTE": (600, 0, 10**6),
    "RUNBOOK_QUERY_EVIDENCE_MAX_CHARS": (500, 1, 10**6),
}

# 浮点取值：环境变量 → (默认值, 最小值, 最大值)
_FLOAT_CONFIG: dict[str, tuple[float, float, float]] = {
    "RUNBOOK_FILTER_SOFT_PENALTY": (0.5, 0.0, 1.0),
}

_TRUE_VALUES = {"1", "true", "yes"}
_FALSE_VALUES = {"0", "false", "no"}

_DOTENV_PATHS = (Path("runtime/.env"), Path(".env"))


def load_dotenv_config(paths: tuple[Path, ...] = _DOTENV_PATHS) -> None:
    """启动时加载 .env（不覆盖已存在的环境变量）。

    顺序：runtime/.env 优先（数据目录，gitignored），其次是项目根 .env。
    显式 export 的环境变量永远优先于 .env 文件。
    """
    for path in paths:
        if path.is_file():
            load_dotenv(dotenv_path=path, override=False)


def validate_startup_config() -> list[str]:
    """校验启动配置，返回问题列表（空 = 全部合法）。

    错误信息只点名变量与合法范围，绝不包含实际取值中的密钥（见
    _llm_missing 与测试 test_validation_errors_do_not_contain_key_values）。
    """
    problems: list[str] = []

    for name, (allowed, default) in _ENUM_CONFIG.items():
        value = os.getenv(name, default).strip().lower()
        if value not in allowed:
            problems.append(
                f"{name}={os.getenv(name)!r} 不合法（可选：{', '.join(sorted(allowed))}）"
            )

    for name in _BOOL_CONFIG:
        value = os.getenv(name, "1").strip().lower()
        if value not in _TRUE_VALUES and value not in _FALSE_VALUES:
            problems.append(f"{name}={os.getenv(name)!r} 不合法（可选：1/true/yes/0/false/no）")

    for name, (default, minimum, maximum) in _INT_CONFIG.items():
        raw = os.getenv(name)
        if raw is None:
            continue
        try:
            value = int(raw)
        except ValueError:
            problems.append(f"{name}={raw!r} 必须是整数（默认 {default}）")
            continue
        if not (minimum <= value <= maximum):
            problems.append(
                f"{name}={value} 超出范围 [{minimum}, {maximum}]（默认 {default}）"
            )

    for name, (default, minimum, maximum) in _FLOAT_CONFIG.items():
        raw = os.getenv(name)
        if raw is None:
            continue
        try:
            value = float(raw)
        except ValueError:
            problems.append(f"{name}={raw!r} 必须是数字（默认 {default}）")
            continue
        if not (minimum <= value <= maximum):
            problems.append(
                f"{name}={value} 超出范围 [{minimum}, {maximum}]（默认 {default}）"
            )

    problems.extend(_llm_missing_parts())
    return problems


def _llm_missing_parts() -> list[str]:
    """LLM_PROVIDER=openai_compatible 时要求三件套齐全（坏配置启动即报错）。"""
    if os.getenv("LLM_PROVIDER", "mock").strip().lower() != "openai_compatible":
        return []
    missing = [
        name for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
        if not os.getenv(name, "").strip()
    ]
    if not missing:
        return []
    # 只点名缺失项，不输出任何变量值（密钥不回显）
    return [f"LLM_PROVIDER=openai_compatible 需要同时设置：{', '.join(missing)}"]


def prepare_config() -> None:
    """create_app 入口：加载 .env + 校验，坏配置直接 RuntimeError（F17）。"""
    load_dotenv_config()
    problems = validate_startup_config()
    if problems:
        raise RuntimeError(
            "启动配置错误（详见 README「配置」节与基线 F17）：\n" + "\n".join(problems)
        )
