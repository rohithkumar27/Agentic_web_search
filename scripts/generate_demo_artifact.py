from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app


SHOWCASE_QUERY = "AI startups in healthcare"


def main() -> int:
    out_dir = Path("docs") / "demo_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)
    response = client.post("/search", json={"query": SHOWCASE_QUERY, "max_results": 10})
    if response.status_code != 200:
        raise RuntimeError(f"search failed: status={response.status_code}, body={response.text}")

    search_payload = response.json()
    run_id = search_payload["run_id"]

    export_response = client.get(f"/export/{run_id}.json")
    if export_response.status_code != 200:
        raise RuntimeError(f"export failed: status={export_response.status_code}, body={export_response.text}")

    export_payload = export_response.json()

    required_keys = {"run_id", "query", "saved_at", "result"}
    missing = sorted(required_keys.difference(export_payload.keys()))
    if missing:
        raise RuntimeError(f"export payload missing keys: {missing}")

    export_path = out_dir / "showcase_export.json"
    export_path.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")

    summary_path = out_dir / "demo_summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# Demo Artifact Summary",
                "",
                f"Generated at: {datetime.now(UTC).isoformat()}",
                f"Run ID: {run_id}",
                f"Query: {SHOWCASE_QUERY}",
                f"Entities: {len(search_payload.get('entities', []))}",
                f"Latency (ms): {search_payload.get('metrics', {}).get('latency_ms', 0)}",
                f"Pages crawled: {search_payload.get('metrics', {}).get('pages_crawled', 0)}",
                f"Errors: {len(search_payload.get('metrics', {}).get('errors', []))}",
                f"Export file: {export_path.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Created {export_path}")
    print(f"Created {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
