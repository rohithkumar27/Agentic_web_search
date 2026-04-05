from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


def _http_post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def _is_traceable(entity: dict[str, Any]) -> bool:
    evidence = entity.get("field_evidence", {}) or {}
    for field_name in ("entity_name", "category", "description", "website", "location"):
        value = entity.get(field_name)
        if value is None:
            continue
        field_ev = evidence.get(field_name)
        if not isinstance(field_ev, dict):
            return False
        if not field_ev.get("source_url") or not field_ev.get("evidence_snippet"):
            return False
    return True


def _evaluate(result: dict[str, Any], heuristics: dict[str, Any]) -> tuple[bool, list[str]]:
    entities = result.get("entities", []) or []
    metrics = result.get("metrics", {}) or {}

    reasons: list[str] = []

    if len(entities) < int(heuristics.get("min_entities", 0)):
        reasons.append(f"entities<{heuristics.get('min_entities')}")

    max_latency = heuristics.get("max_latency_ms")
    if max_latency is not None and int(metrics.get("latency_ms", 0)) > int(max_latency):
        reasons.append(f"latency>{max_latency}")

    max_errors = heuristics.get("max_errors")
    if max_errors is not None and len(metrics.get("errors", []) or []) > int(max_errors):
        reasons.append(f"errors>{max_errors}")

    if heuristics.get("require_traceability", False):
        not_traceable = [e.get("entity_name", "unknown") for e in entities if not _is_traceable(e)]
        if not_traceable:
            reasons.append(f"non_traceable:{','.join(not_traceable[:3])}")

    return len(reasons) == 0, reasons


def _build_requester(endpoint: str, timeout: int, in_process: bool) -> Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]:
    if not in_process:
        return lambda payload: _http_post_json(endpoint, payload, timeout)

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    def _request(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        resp = client.post("/search", json=payload)
        return resp.status_code, resp.json()

    return _request


def main() -> int:
    parser = argparse.ArgumentParser(description="Run benchmark queries against /search.")
    parser.add_argument("--queries", default="tests/benchmark_queries.json")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/search")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit if any case fails.")
    parser.add_argument("--in-process", action="store_true", help="Run benchmarks against FastAPI TestClient.")
    args = parser.parse_args()

    queries_path = Path(args.queries)
    queries = json.loads(queries_path.read_text(encoding="utf-8-sig"))

    requester = _build_requester(endpoint=args.endpoint, timeout=args.timeout, in_process=args.in_process)

    report_rows: list[dict[str, Any]] = []
    passed = 0

    for spec in queries:
        case_id = spec["id"]
        payload = {
            "query": spec["query"],
            "max_results": int(spec.get("max_results", 10)),
        }
        heuristics = spec.get("heuristics", {})

        try:
            status, body = requester(payload)
            if status != 200:
                ok, reasons = False, [f"http_status:{status}"]
            else:
                ok, reasons = _evaluate(body, heuristics)
        except (TimeoutError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
            ok, reasons = False, [f"request_error:{exc}"]
            body = {}
        except Exception as exc:
            ok, reasons = False, [f"runtime_error:{exc}"]
            body = {}

        if ok:
            passed += 1

        report_rows.append(
            {
                "id": case_id,
                "query": spec["query"],
                "passed": ok,
                "reasons": reasons,
                "metrics": body.get("metrics", {}),
                "entity_count": len(body.get("entities", []) or []),
            }
        )

        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] {case_id} :: {','.join(reasons) if reasons else 'ok'}")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "endpoint": args.endpoint,
        "in_process": args.in_process,
        "total": len(report_rows),
        "passed": passed,
        "failed": len(report_rows) - passed,
        "results": report_rows,
    }

    out_dir = Path("docs") / "benchmark_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nSummary: {passed}/{len(report_rows)} passed")
    print(f"Report: {out_path}")

    if args.strict and passed != len(report_rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
