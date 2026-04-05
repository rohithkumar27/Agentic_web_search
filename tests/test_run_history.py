from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, get_pipeline, get_run_store
from app.storage.run_store import RunStore
from tests.test_search_endpoint import _pipeline, FakeScraper


_DEF_BASE = Path(".test_runs")


def _new_run_store() -> RunStore:
    base_dir = _DEF_BASE / f"run_store_{uuid.uuid4().hex}"
    base_dir.mkdir(parents=True, exist_ok=True)
    return RunStore(base_dir=base_dir)


def test_run_history_and_export_lifecycle() -> None:
    run_store = _new_run_store()
    app.dependency_overrides[get_pipeline] = lambda: _pipeline(FakeScraper())
    app.dependency_overrides[get_run_store] = lambda: run_store

    try:
        client = TestClient(app)

        create_response = client.post(
            "/search",
            json={"query": "ai startups in healthcare", "max_results": 2},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        run_id = created["run_id"]

        get_response = client.get(f"/runs/{run_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["run_id"] == run_id
        assert fetched["entities"] == created["entities"]

        export_response = client.get(f"/export/{run_id}.json")
        assert export_response.status_code == 200
        exported = export_response.json()
        assert exported["run_id"] == run_id
        assert exported["query"] == "ai startups in healthcare"
        assert exported["result"]["run_id"] == run_id

    finally:
        app.dependency_overrides.clear()


def test_run_history_returns_404_for_missing_run() -> None:
    run_store = _new_run_store()
    app.dependency_overrides[get_run_store] = lambda: run_store

    try:
        client = TestClient(app)

        get_response = client.get("/runs/run_missing")
        export_response = client.get("/export/run_missing.json")

        assert get_response.status_code == 404
        assert export_response.status_code == 404

    finally:
        app.dependency_overrides.clear()
