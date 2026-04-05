from __future__ import annotations

import os
from typing import Any

from app.services.extractor import StructuredLLMClient


class StructuredLLMConfigurationError(RuntimeError):
    """Raised when LLM provider configuration is missing or invalid."""


class OpenAICompatibleStructuredLLMClient(StructuredLLMClient):
    """Structured extraction client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        response_mode: str = "json_schema",
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLM clients") from exc

        self._model = model
        self._response_mode = response_mode
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def complete(self, prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
        req: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        }

        if self._response_mode == "json_schema":
            req["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction_output",
                    "schema": schema,
                    "strict": True,
                },
            }
        else:
            req["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**req)
        content = response.choices[0].message.content
        if content is None:
            return {"entities": []}
        return content


def _build_openai_client() -> StructuredLLMClient:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise StructuredLLMConfigurationError("OPENAI_API_KEY is not set.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    return OpenAICompatibleStructuredLLMClient(
        api_key=api_key,
        model=model,
        response_mode="json_schema",
    )


def _build_groq_client() -> StructuredLLMClient:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise StructuredLLMConfigurationError("GROQ_API_KEY is not set.")

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
    return OpenAICompatibleStructuredLLMClient(
        api_key=api_key,
        model=model,
        base_url="https://api.groq.com/openai/v1",
        response_mode="json_object",
    )


def _build_langchain_client() -> StructuredLLMClient:
    # Build a LangChain-backed client if requested. This keeps the same
    # StructuredLLMClient interface but delegates generation to langchain.
    model = os.getenv("LLM_LANGCHAIN_MODEL", "gpt-4o").strip() or "gpt-4o"
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    try:
        from app.services.langchain_client import LangChainStructuredLLMClient
    except Exception as exc:
        raise StructuredLLMConfigurationError("Failed to import LangChain client") from exc

    return LangChainStructuredLLMClient(model=model, api_key=api_key, response_mode="json_schema")


def get_structured_llm_client() -> StructuredLLMClient:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower() or "openai"

    if provider == "openai":
        return _build_openai_client()
    if provider == "groq":
        return _build_groq_client()
    if provider == "langchain":
        return _build_langchain_client()

    raise StructuredLLMConfigurationError(f"Unsupported LLM_PROVIDER: {provider}")
