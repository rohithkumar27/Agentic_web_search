from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ExtractorError(Exception):
    """Raised when structured extraction fails after retries."""


class ExtractedFieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    source_url: str = Field(min_length=1, max_length=2048)
    evidence_snippet: str = Field(min_length=1, max_length=500)


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    website: str | None = Field(default=None, max_length=2048)
    location: str | None = Field(default=None, max_length=200)
    key_attributes: dict[str, Any] = Field(default_factory=dict)
    field_evidence: dict[str, ExtractedFieldEvidence] = Field(default_factory=dict)


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[ExtractedEntity] = Field(default_factory=list)


class StructuredLLMClient(Protocol):
    def complete(self, prompt: str, schema: dict[str, Any]) -> str | dict[str, Any]:
        """Return structured response content as JSON string or dict."""


class EntityExtractor:
    def __init__(
        self,
        client: StructuredLLMClient,
        max_retries: int = 1,
        max_input_chars: int = 12000,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._max_input_chars = max_input_chars

    def extract(self, query: str, source_url: str, page_text: str, max_entities: int = 20) -> ExtractionOutput:
        clipped_text = page_text[: self._max_input_chars]
        prompt = self._build_prompt(
            query=query,
            source_url=source_url,
            page_text=clipped_text,
            max_entities=max_entities,
        )
        schema = ExtractionOutput.model_json_schema()
        schema = self._prepare_schema_for_openai(schema)

        output = self._run_with_retries(prompt=prompt, schema=schema)
        if output.entities:
            return output

        # Recovery pass for providers that frequently return empty lists on the first pass.
        recovery_prompt = self._build_non_empty_recovery_prompt(
            query=query,
            source_url=source_url,
            page_text=clipped_text,
            max_entities=max_entities,
        )
        recovery_output = self._run_with_retries(prompt=recovery_prompt, schema=schema)
        return recovery_output

    def _prepare_schema_for_openai(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Patch schema for OpenAI strict json_schema compatibility."""
        def patch_node(node: Any) -> None:
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict):
                    # OpenAI strict json_schema requires all property keys to appear in required.
                    node["required"] = list(props.keys())
                    # OpenAI strict json_schema also requires explicit additionalProperties handling.
                    node["additionalProperties"] = False

                if node.get("type") == "object" and "properties" not in node and "additionalProperties" not in node:
                    node["additionalProperties"] = False

                for value in node.values():
                    patch_node(value)
            elif isinstance(node, list):
                for item in node:
                    patch_node(item)

        patch_node(schema)
        return schema

    def _run_with_retries(self, prompt: str, schema: dict[str, Any]) -> ExtractionOutput:
        last_error: Exception | None = None
        candidate_prompt = prompt

        for _ in range(self._max_retries + 1):
            raw = self._client.complete(prompt=candidate_prompt, schema=schema)
            try:
                return self._parse_output(raw)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last_error = exc
                candidate_prompt = self._repair_prompt(candidate_prompt)

        raise ExtractorError("Structured extraction failed after retries.") from last_error

    def _parse_output(self, raw: str | dict[str, Any]) -> ExtractionOutput:
        payload = self._load_payload(raw)
        normalized = self._normalize_payload(payload)
        return ExtractionOutput.model_validate(normalized)

    def _load_payload(self, raw: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if not isinstance(raw, str):
            raise TypeError("Unsupported model output type.")

        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(text[start : end + 1])
            else:
                raise

        if isinstance(parsed, list):
            return {"entities": parsed}
        if isinstance(parsed, dict):
            return parsed
        raise TypeError("Unsupported JSON payload type.")

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        unwrapped = payload
        for wrapper_key in ("result", "output", "data"):
            maybe = unwrapped.get(wrapper_key)
            if isinstance(maybe, dict) and "entities" in maybe:
                unwrapped = maybe
                break

        entities = unwrapped.get("entities")
        if not isinstance(entities, list):
            entities = []

        normalized_entities: list[dict[str, Any]] = []
        for entity in entities:
            if not isinstance(entity, dict):
                continue

            entity_name = str(entity.get("entity_name") or "").strip()[:200]
            if not entity_name:
                continue

            normalized_entity = {
                "entity_name": entity_name,
                "category": self._clip_nullable(entity.get("category"), 100),
                "description": self._clip_nullable(entity.get("description"), 1000),
                "website": self._clip_nullable(entity.get("website"), 2048),
                "location": self._clip_nullable(entity.get("location"), 200),
                "key_attributes": entity.get("key_attributes") if isinstance(entity.get("key_attributes"), dict) else {},
                "field_evidence": self._normalize_field_evidence(entity.get("field_evidence")),
            }
            normalized_entities.append(normalized_entity)

        return {"entities": normalized_entities}

    def _normalize_field_evidence(self, raw_map: Any) -> dict[str, Any]:
        if not isinstance(raw_map, dict):
            return {}

        normalized: dict[str, Any] = {}
        for field_name, evidence in raw_map.items():
            if not isinstance(evidence, dict):
                continue
            source_url = str(evidence.get("source_url") or "").strip()[:2048]
            snippet = str(evidence.get("evidence_snippet") or "").strip()
            snippet = " ".join(snippet.split())[:500]
            if not source_url or not snippet:
                continue
            normalized[str(field_name)] = {
                "value": evidence.get("value"),
                "source_url": source_url,
                "evidence_snippet": snippet,
            }
        return normalized

    def _clip_nullable(self, value: Any, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text[:limit]

    def _build_prompt(self, query: str, source_url: str, page_text: str, max_entities: int) -> str:
        return (
            "You are an information extraction engine.\n"
            "Return JSON only, matching the provided schema exactly.\n"
            "Rules:\n"
            "1. Extract only entities relevant to the query.\n"
            "2. Do not invent facts.\n"
            "3. For every non-null field, include field_evidence with source_url and literal snippet.\n"
            "4. If relevant entities are present in text, do not return an empty entities array.\n"
            f"5. Use this source_url for evidence unless a better in-page URL is explicit: {source_url}\n"
            f"6. Limit entities to at most {max_entities}.\n\n"
            f"Query: {query}\n"
            "Page text:\n"
            f"{page_text}"
        )

    def _build_non_empty_recovery_prompt(self, query: str, source_url: str, page_text: str, max_entities: int) -> str:
        return (
            "You returned zero entities previously. Try again carefully.\n"
            "Return JSON only with key: entities (array).\n"
            "Goal: extract named companies/startups/products relevant to query.\n"
            "Minimum target: if at least one clear candidate exists, return at least 1 entity.\n"
            "For each entity, always include entity_name and field_evidence.entity_name with source_url and snippet.\n"
            "Other fields may be null if uncertain.\n"
            f"Query: {query}\n"
            f"Source URL: {source_url}\n"
            f"Max entities: {max_entities}\n"
            "Page text:\n"
            f"{page_text}"
        )

    def _repair_prompt(self, prompt: str) -> str:
        return (
            f"{prompt}\n\n"
            "Your previous output was invalid. Return valid JSON only and strictly match the schema."
        )



