# 3-Minute Demo Script

## Goal
Show end-to-end trustable entity discovery from query to evidence-backed export.

## Demo Flow (Approx. 3 Minutes)
1. `00:00-00:20` Open `http://127.0.0.1:8000/` and briefly explain the challenge objective.
2. `00:20-00:50` Enter query: `AI startups in healthcare` and click **Run Search**.
3. `00:50-01:20` Highlight metrics panel: run id, latency, pages crawled, estimated cost.
4. `01:20-01:55` Show sortable confidence column and category filter.
5. `01:55-02:30` Open evidence drawer from a table cell and call out source URL + snippet traceability.
6. `02:30-02:50` Click **Export JSON** and show the structured payload.
7. `02:50-03:00` Close with architecture summary and current milestone status.

## Backup Demo Artifact
If live APIs are unstable, generate and present a fresh local export artifact:
1. Run `python scripts/generate_demo_artifact.py`
2. Show output files in `docs/demo_artifacts/`:
   - `showcase_export.json`
   - `demo_summary.md`

## Talking Points
1. Every non-null field is designed to map to evidence.
2. Partial failures are isolated and reported in metrics errors.
3. Runs are reproducible via run id and export endpoints.
