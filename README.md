# Agentic Search Challenge

## Overview
Agentic Search accepts a topic query, discovers relevant sources, and returns structured entities with confidence and source-traceable evidence.

Current implementation includes:
1. End-to-end API pipeline (`POST /search`).
2. Browser UI (`GET /`) with table, filters, metrics, and evidence drawer.
3. Run persistence + replay/export (`GET /runs/{run_id}`, `GET /export/{run_id}.json`).
4. Benchmark pack + runner.
5. Demo artifact generation script.
6. Pluggable LLM provider config (`openai` or `groq`).

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Configure `.env` (see examples below).
4. Run app:
   `uvicorn app.main:app --reload`
5. Open UI:
   `http://127.0.0.1:8000/`

## LLM Provider Setup
### Groq (recommended for your case)
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
SERPAPI_API_KEY=your_serpapi_key
```

### OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4.1-mini
SERPAPI_API_KEY=your_serpapi_key
```

Notes:
1. `SERPAPI_API_KEY` is required for live search results.
2. If provider keys are missing/invalid, app falls back to null extraction (safe mode, low recall).

## API Endpoints
- `GET /` - interactive results UI.
- `GET /health` - service health.
- `POST /search` - execute full pipeline.
- `GET /runs/{run_id}` - fetch saved run response.
- `GET /export/{run_id}.json` - fetch saved run artifact.

## Architecture
See [docs/architecture.md](docs/architecture.md) for components and request lifecycle.

## Tests
Core regression slice:
`pytest -q tests/test_llm_factory.py tests/test_main_config.py tests/test_ui.py tests/test_search_endpoint.py tests/test_run_history.py tests/test_extractor.py tests/test_evidence_validator.py tests/test_normalization.py tests/test_dedupe.py tests/test_scoring.py -o addopts='-p no:cacheprovider' --basetemp e:\CIIR_Challenge\.pytest_runbase`

## Benchmarking
Run in-process (no separate server):
`python scripts/run_benchmarks.py --in-process`

Run against local server:
`python scripts/run_benchmarks.py --endpoint http://127.0.0.1:8000/search`

Strict mode (non-zero exit if any fail):
`python scripts/run_benchmarks.py --in-process --strict`

## Demo Readiness
- Demo runbook: [docs/demo_script.md](docs/demo_script.md)
- Generate backup artifact: `python scripts/generate_demo_artifact.py`
- Artifacts: `docs/demo_artifacts/`

## Current Milestone Status
- Milestone 0: complete
- Milestone 1: complete
- Milestone 2: complete
- Milestone 3: complete
- Milestone 4: complete
- Milestone 5: complete
- Milestone 6: complete
