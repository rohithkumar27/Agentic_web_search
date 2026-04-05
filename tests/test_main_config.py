import os

from app.main import NullStructuredLLMClient, get_extractor_client


def test_get_extractor_client_uses_null_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = get_extractor_client()
    assert isinstance(client, NullStructuredLLMClient)


def test_get_extractor_client_falls_back_on_initialization_error(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _explode():
        raise RuntimeError("boom")

    monkeypatch.setattr("app.main.get_structured_llm_client", _explode)

    client = get_extractor_client()
    assert isinstance(client, NullStructuredLLMClient)


def test_get_extractor_client_supports_groq_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")

    class _StubClient:
        def complete(self, prompt: str, schema: dict):
            return {"entities": []}

    monkeypatch.setattr("app.main.get_structured_llm_client", lambda: _StubClient())

    client = get_extractor_client()
    assert hasattr(client, "complete")
