# Agentic Search Challenge - Winning Blueprint

## 1) Product Goal
Build an agentic search system that accepts a topic query and returns a high-quality, source-traceable table of entities with useful attributes, good latency, and practical cost.

Deadline target: Saturday, April 4, 2026, 11:59 PM EDT.

## 2) Winning Differentiators
1. Strict traceability for every populated field.
2. Quality controls: schema validation, deduplication, confidence scoring.
3. Practical engineering: caching, fallbacks, error handling, metrics.
4. Polished delivery: API + UI + export + clear documentation.

## 3) Tech Stack (Recommended)
1. Backend: FastAPI + Pydantic
2. Search: SerpAPI (with Brave fallback if needed)
3. Scraping: httpx + trafilatura + BeautifulSoup fallback
4. LLM extraction: OpenAI structured JSON output
5. Storage/cache: SQLite + local page cache
6. Frontend: React/Next.js table UI (or minimal FastAPI templates if needed)

## 4) End-to-End Pipeline
1. Accept user query.
2. Search web for top N relevant URLs.
3. Crawl and clean each page.
4. Chunk text and run LLM extraction.
5. Validate and normalize extracted entities.
6. Deduplicate and merge cross-source duplicates.
7. Score confidence.
8. Return final structured table with evidence and metrics.

## 5) Data Contracts

### 5.1 Entity Output Schema
- entity_id
- entity_name
- category
- description
- website
- location
- key_attributes (object)
- confidence_score (0 to 1)
- sources (array of URLs)
- field_evidence (map)
  - each field maps to:
    - value
    - source_url
    - evidence_snippet

### 5.2 Run Metadata Schema
- run_id
- query
- started_at
- finished_at
- search_results_count
- pages_crawled
- tokens_used
- estimated_cost
- latency_ms
- errors

## 6) API Blueprint
1. POST /search
- Input: { query: string, max_results?: int }
- Output: { run_id, entities: [...], metrics: {...} }

2. GET /runs/{run_id}
- Returns full run details, including intermediate and final artifacts.

3. GET /export/{run_id}.json
- Exports final structured result JSON.

4. GET /health
- Basic health and readiness status.

## 7) LLM Extraction Rules
1. Extract only entities relevant to query intent.
2. Never invent unsupported values.
3. If uncertain, return null and lower confidence.
4. Every non-null field must include source URL and evidence snippet.
5. Keep evidence snippets short and literal from source text.

## 8) Quality Engine

### 8.1 Validation
1. Enforce JSON schema.
2. Validate URL formats.
3. Ensure evidence exists for every non-null field.

### 8.2 Deduplication
1. Normalize entity names (case/punctuation normalization).
2. Merge by domain and high name similarity.
3. Combine sources and keep strongest evidence per field.

### 8.3 Confidence Scoring
Weighted score based on:
1. Evidence quality
2. Source diversity
3. Cross-source consistency
4. Completeness and contradiction penalties

## 9) Frontend Blueprint
1. Query input and run trigger.
2. Sortable results table.
3. Per-cell evidence drawer ("why this value").
4. Filters by confidence/category.
5. Export JSON button.
6. Run metrics panel (latency, pages, estimated cost).

## 10) Suggested Repository Structure
1. app/main.py
2. app/api/routes.py
3. app/models/schemas.py
4. app/services/search_client.py
5. app/services/scraper.py
6. app/services/extractor.py
7. app/services/dedupe.py
8. app/services/scoring.py
9. app/storage/db.py
10. web/
11. tests/
12. docs/architecture.md
13. README.md

## 11) Step-by-Step Implementation Plan
1. Scaffold backend and core schemas, add /health.
2. Integrate search provider.
3. Implement scraper with fallback + caching.
4. Implement LLM structured extraction.
5. Add traceability enforcement layer.
6. Add dedupe/merge logic.
7. Add confidence scoring.
8. Wire end-to-end /search pipeline.
9. Build frontend table + evidence drawer.
10. Add export endpoint + run history.
11. Add tests: schema, dedupe, pipeline smoke.
12. Final polish: docs, architecture, demo prep.

## 12) Judging-Optimized Submission Checklist
1. Working app (API plus optional UI)
2. Public GitHub repository
3. README with setup, design choices, trade-offs, limitations
4. Architecture diagram
5. Example outputs for multiple queries
6. Optional live demo URL
7. Submission email with exact subject:
   CIIR challenge submission

## 13) Time Plan (Mar 30 to Apr 4)
1. Mar 30: Scaffold backend, schemas, health endpoint
2. Mar 31: Search + scraping pipeline working
3. Apr 1: LLM extraction + validation + traceability
4. Apr 2: Dedupe + confidence + metrics
5. Apr 3: Frontend + export + tests
6. Apr 4: Documentation, demo script/video, deployment polish

