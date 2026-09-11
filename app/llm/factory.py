import os
import time

from app.llm.base import DiagnosisResult, LLMClient
from app.llm.mock_client import MockLLMClient
from app.llm.openai_compatible_client import OpenAICompatibleClient


class FallbackLLMClient:
    """主后端失败时降级到 mock，并在结果里如实记录降级元数据（F09）。"""

    def __init__(self, primary: LLMClient, fallback: MockLLMClient | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or MockLLMClient()

    def diagnose(self, **kwargs) -> DiagnosisResult:
        started = time.perf_counter()
        try:
            return self.primary.diagnose(**kwargs)
        except Exception as exc:
            result = self.fallback.diagnose(**kwargs)
            return DiagnosisResult(
                diagnosis=result.diagnosis,
                provider="mock_fallback",
                requested_provider=getattr(self.primary, "provider_name", "unknown"),
                model=getattr(self.primary, "model", None),
                fallback_reason=_brief_error(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider != "openai_compatible":
        return MockLLMClient()

    try:
        primary = OpenAICompatibleClient(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", ""),
        )
    except Exception as exc:
        return _MockFallbackClient(fallback_reason=_brief_error(exc))
    return FallbackLLMClient(primary=primary)


class _MockFallbackClient(MockLLMClient):
    """openai_compatible 客户端构造失败（坏配置）时的降级客户端（F09）。"""

    def __init__(self, fallback_reason: str | None = None) -> None:
        self.fallback_reason = fallback_reason

    def diagnose(self, **kwargs) -> DiagnosisResult:
        started = time.perf_counter()
        result = super().diagnose(**kwargs)
        return DiagnosisResult(
            diagnosis=result.diagnosis,
            provider="mock_fallback",
            requested_provider="openai_compatible",
            fallback_reason=self.fallback_reason,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )


def _brief_error(exc: Exception) -> str:
    """异常摘要：类型 + 截断消息（不携带完整堆栈，避免 Trace 爆炸）。"""
    message = " ".join(str(exc).split())  # 压平换行，保持 Trace 单行可读
    return f"{type(exc).__name__}: {message[:200]}"
