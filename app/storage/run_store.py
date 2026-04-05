from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models.schemas import SearchResponse


class RunStore:
    def __init__(self, base_dir: str | Path = ".cache/runs") -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, query: str, result: SearchResponse) -> None:
        payload = {
            "run_id": result.run_id,
            "query": query,
            "saved_at": datetime.now(UTC).isoformat(),
            "result": result.model_dump(mode="json"),
        }
        self._path_for(result.run_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_result(self, run_id: str) -> SearchResponse | None:
        payload = self._load_payload(run_id)
        if payload is None:
            return None
        return SearchResponse.model_validate(payload["result"])

    def export_payload(self, run_id: str) -> dict[str, Any] | None:
        payload = self._load_payload(run_id)
        if payload is None:
            return None
        return payload

    def _load_payload(self, run_id: str) -> dict[str, Any] | None:
        path = self._path_for(run_id)
        if not path.exists():
            return None

        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict) or "result" not in payload:
            return None

        return payload

    def _path_for(self, run_id: str) -> Path:
        safe_run_id = run_id.replace("/", "_").replace("\\", "_")
        return self._base_dir / f"{safe_run_id}.json"
