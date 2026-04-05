import pytest

from app.services.openai_client import StructuredLLMConfigurationError, get_structured_llm_client


class _DummyClient:
    def complete(self, prompt: str, schema: dict):
        return {"entities": []}


def test_factory_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(StructuredLLMConfigurationError):
        get_structured_llm_client()


def test_factory_requires_openai_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(StructuredLLMConfigurationError):
        get_structured_llm_client()


def test_factory_requires_groq_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(StructuredLLMConfigurationError):
        get_structured_llm_client()
