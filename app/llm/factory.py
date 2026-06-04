import os

from app.llm.base import DiagnosisResult, LLMClient
from app.llm.mock_client import MockLLMClient
from app.llm.openai_compatible_client import OpenAICompatibleClient


class FallbackLLMClient:
    def __init__(self, primary: LLMClient, fallback: MockLLMClient | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or MockLLMClient()

    def diagnose(self, **kwargs) -> DiagnosisResult:
        try:
            return self.primary.diagnose(**kwargs)
        except Exception:
            result = self.fallback.diagnose(**kwargs)
            return DiagnosisResult(diagnosis=result.diagnosis, provider="mock_fallback")


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
    except Exception:
        return _MockFallbackClient()
    return FallbackLLMClient(primary=primary)


class _MockFallbackClient(MockLLMClient):
    def diagnose(self, **kwargs) -> DiagnosisResult:
        result = super().diagnose(**kwargs)
        return DiagnosisResult(diagnosis=result.diagnosis, provider="mock_fallback")
