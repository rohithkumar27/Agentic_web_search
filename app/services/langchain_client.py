from __future__ import annotations

import os
from typing import Any

from app.services.extractor import StructuredLLMClient


class LangChainStructuredLLMClient(StructuredLLMClient):
    """Simple LangChain-based Structured LLM client.

    This wrapper uses `ChatOpenAI` to produce text output that the
    existing extractor can parse as JSON. It keeps the same
    `complete(prompt, schema)` interface used in the repo.
    """

    def __init__(self, model: str, api_key: str | None = None, response_mode: str = "json_schema") -> None:
        self._chat_openai_cls = None
        try:
            from langchain_openai import ChatOpenAI

            self._chat_openai_cls = ChatOpenAI
        except ImportError as exc:
            try:
                # Compatibility fallback for older LangChain installs.
                from langchain.chat_models import ChatOpenAI

                self._chat_openai_cls = ChatOpenAI
            except ImportError:
                raise RuntimeError(
                    "LangChain OpenAI integration is required. Install `langchain-openai`."
                ) from exc

        # If an API key was provided, ensure it's available for langchain/OpenAI
        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)

        self._model = model
        self._response_mode = response_mode
        self._llm = self._chat_openai_cls(model=model, temperature=0)

    def complete(self, prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
        # Prepend a system instruction asking for strict JSON to help the extractor
        full_prompt = "Return strict JSON only.\n\n" + prompt
        response = self._llm.invoke(full_prompt)
        if isinstance(response, str):
            return response
        content = getattr(response, "content", response)
        return content if content is not None else '{"entities":[]}'
