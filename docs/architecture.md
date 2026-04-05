# Architecture

## System Overview
Agentic Search is a FastAPI application that turns a natural-language topic query into structured entities with evidence, confidence, and exportable run history.

Core capabilities:
1. Search and URL discovery.
2. Web scraping with extraction fallback and cache reuse.
3. Structured entity extraction and evidence validation.
4. Deduplication, merge, and confidence scoring.
5. API + browser UI for interactive review and export.

## Components
- `app/main.py`: HTTP entrypoints (`/`, `/search`, `/runs/{run_id}`, `/export/{run_id}.json`, `/health`).
- `app/services/search_client.py`: Provider abstraction and SerpAPI adapter.
- `app/services/scraper.py`: Page fetch, text extraction, fallback parsing.
- `app/storage/page_cache.py`: URL-keyed page cache with TTL.
- `app/services/extractor.py`: Structured extraction contract + parser guardrails.
- `app/services/evidence_validator.py`: Traceability enforcement and snippet normalization.
- `app/services/normalization.py`: Name/domain/category/location normalization.
- `app/services/dedupe.py`: Entity clustering and merge with provenance preservation.
- `app/services/scoring.py`: Confidence scoring engine in [0,1].
- `app/services/pipeline.py`: End-to-end orchestration.
- `app/storage/run_store.py`: Run persistence and export payload retrieval.
- `app/ui/index.html`: Browser UI (form, table, metrics, evidence drawer).

## Request Lifecycle
1. User submits query from UI (`POST /search`) or direct API.
2. Pipeline calls search provider and normalizes top results.
3. Each URL is scraped (with cache lookup first).
4. Extractor produces structured entities per page.
5. Evidence validator removes untraceable fields/entities.
6. Deduper merges cross-source duplicates.
7. Scorer computes confidence for each merged entity.
8. API returns `SearchResponse` and persists run artifact.
9. UI renders sortable/filterable table and evidence drawer.
10. User can retrieve run via `/runs/{run_id}` or export via `/export/{run_id}.json`.

## Data Flow Diagram
```text
[Browser UI] --POST /search--> [FastAPI]
   ^                              |
   |                              v
GET /runs, /export            [SearchPipeline]
                                  |
                                  +--> [Search Client] -> URLs
                                  +--> [Scraper + PageCache] -> page text
                                  +--> [Extractor] -> raw entities
                                  +--> [EvidenceValidator] -> traceable entities
                                  +--> [Deduper] -> merged entities
                                  +--> [ConfidenceScorer] -> ranked entities
                                  |
                                  +--> [RunStore] -> saved run artifact
```

## Design Choices and Trade-offs
1. Provider abstraction for search isolates quota or vendor changes.
2. Strict evidence gating prioritizes trust over recall.
3. File-backed run store is simple and auditable, but not optimized for high concurrency.
4. In-app HTML UI reduces setup complexity; trade-off is less component reusability than React.
5. Pipeline catches partial failures and returns best-effort output instead of hard-failing entire runs.

## Known Limitations
1. Default extractor client is a placeholder and returns empty entities until a real LLM client is wired.
2. Full benchmark quality depends on live search/API availability.
3. Some Windows environments may need custom pytest temp settings due path permission quirks.

## Future Improvements
1. Wire real OpenAI structured-output extractor.
2. Add async crawling for throughput.
3. Move run storage to SQLite for query and pagination.
4. Add authentication/rate limiting for production deployment.
