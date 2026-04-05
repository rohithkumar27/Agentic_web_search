# Agentic Search - Engineering Execution Plan

This plan is designed for high-confidence delivery: small increments, strict verification, and no hidden coupling.

## Execution Rules
1. Build in vertical slices (code + test + verification together).
2. No new step starts until the current step passes exit criteria.
3. Every feature must have at least one automated verification.
4. Keep commits small and reversible.
5. Track assumptions explicitly in README as they appear.

## Quality Gates (Global)
1. `lint` passes.
2. `type-check` passes.
3. `unit tests` pass.
4. `pipeline smoke test` passes on at least 2 real queries.
5. Output contains source-traceable evidence for all non-null fields.

## Milestone 0 - Project Foundation
Goal: deterministic local setup and runnable app skeleton.

### Step 0.1 Repository Skeleton
Tasks:
1. Create backend structure (`app/`, `tests/`, `docs/`).
2. Add `pyproject.toml` (or `requirements.txt`) and `.env.example`.
3. Add `Makefile` or task runner aliases.

Deliverables:
1. Initial folder structure and dependency manifest.
2. `README` bootstrap section.

Verification:
1. Install dependencies successfully.
2. Run app process without runtime errors.

Exit Criteria:
1. `GET /health` returns success.

### Step 0.2 Core Schemas and Contracts
Tasks:
1. Define Pydantic models for request, entity, evidence, run metrics.
2. Add strict validation constraints.

Deliverables:
1. `schemas.py` with complete contracts.

Verification:
1. Unit test valid/invalid payloads.

Exit Criteria:
1. Invalid payloads are rejected with clear errors.

## Milestone 1 - Search + Crawl Pipeline
Goal: stable URL discovery and clean text extraction.

### Step 1.1 Search Adapter
Tasks:
1. Implement provider interface (SerpAPI first).
2. Normalize search output to internal `SearchResult`.
3. Add timeout/retry and error mapping.

Deliverables:
1. `search_client.py` abstraction + provider implementation.

Verification:
1. Unit tests with mocked provider responses.
2. Integration check on sample query.

Exit Criteria:
1. Returns normalized top N URLs and titles.

### Step 1.2 Scraper with Fallback
Tasks:
1. Fetch HTML with `httpx`.
2. Extract main text with `trafilatura`.
3. Fallback to `BeautifulSoup` body extraction.
4. Add content length threshold and noise filtering.

Deliverables:
1. `scraper.py` with `fetch_and_extract(url)`.

Verification:
1. Unit tests for extractor fallback behavior.
2. Integration test on 3 URLs (news/blog/company site).

Exit Criteria:
1. At least 2/3 pages produce non-empty cleaned text.

### Step 1.3 Page Cache
Tasks:
1. Hash URL to cache key.
2. Persist raw and cleaned content.
3. TTL-based cache reuse.

Deliverables:
1. Cache utility in `storage/` and cache tests.

Verification:
1. First request writes cache; second request reuses cache.

Exit Criteria:
1. Repeat run latency improves measurably.

## Milestone 2 - LLM Structured Extraction
Goal: extract high-quality entities with evidence.

### Step 2.1 Extraction Prompt + Schema Enforcement
Tasks:
1. Create strict extraction prompt with explicit field rules.
2. Use structured JSON output with model-side schema.
3. Add parser guardrails for malformed responses.

Deliverables:
1. `extractor.py` with deterministic output contract.

Verification:
1. Unit tests for parsing failures and recovery.
2. Golden test with fixed input text.

Exit Criteria:
1. Output always conforms to schema.

### Step 2.2 Evidence Traceability Enforcement
Tasks:
1. For each non-null field, require `source_url` + snippet.
2. Reject/drop fields missing evidence.
3. Add evidence truncation and normalization.

Deliverables:
1. Evidence validator module.

Verification:
1. Unit tests that reject non-traceable fields.

Exit Criteria:
1. 100% non-null fields are traceable.

## Milestone 3 - Merge, Dedupe, Scoring
Goal: produce clean and trustworthy final table.

### Step 3.1 Entity Normalization
Tasks:
1. Normalize names, domains, and categories.
2. Standardize website and location formats.

Deliverables:
1. Normalization helpers.

Verification:
1. Unit tests for normalization edge cases.

Exit Criteria:
1. Canonical output for equivalent variants.

### Step 3.2 Deduplication and Merge
Tasks:
1. Match entities via domain and normalized name similarity.
2. Merge fields with strongest evidence and source union.
3. Preserve provenance through merge.

Deliverables:
1. `dedupe.py`.

Verification:
1. Unit tests with synthetic duplicate clusters.

Exit Criteria:
1. Duplicates collapse correctly without losing evidence.

### Step 3.3 Confidence Scoring
Tasks:
1. Implement scoring formula with weighted features:
   - evidence quality
   - source diversity
   - cross-source agreement
   - completeness/contradiction penalty
2. Clamp to [0,1].

Deliverables:
1. `scoring.py`.

Verification:
1. Unit tests for monotonicity and boundary behavior.

Exit Criteria:
1. High-quality entities rank above weak ones in test set.

## Milestone 4 - End-to-End API
Goal: production-style endpoint with observability.

### Step 4.1 `/search` Orchestration
Tasks:
1. Implement full query -> search -> crawl -> extract -> dedupe -> score flow.
2. Add configurable limits and timeouts.
3. Add graceful partial-failure handling.

Deliverables:
1. `/search` endpoint with run_id and metrics.

Verification:
1. End-to-end test with mocked dependencies.
2. Manual run on 2 real queries.

Exit Criteria:
1. Endpoint returns valid structured response within target latency.

### Step 4.2 Run History + Export
Tasks:
1. Persist run metadata and artifacts.
2. Add `GET /runs/{run_id}` and `GET /export/{run_id}.json`.

Deliverables:
1. DB and retrieval endpoints.

Verification:
1. Integration test for create/read/export lifecycle.

Exit Criteria:
1. Any run can be replayed and audited.

## Milestone 5 - Frontend and Demo UX
Goal: judge-friendly interface and trust visibility.

### Step 5.1 Results Table UI
Tasks:
1. Query form and submit flow.
2. Sortable/filterable table.
3. Confidence badge.

Deliverables:
1. Functional result view.

Verification:
1. Manual UI smoke test desktop/mobile.

Exit Criteria:
1. Query to table flow works end-to-end.

### Step 5.2 Evidence Drawer + Metrics Panel
Tasks:
1. Per-cell evidence drawer with URL and snippet.
2. Metrics panel (latency, pages crawled, estimated cost).

Deliverables:
1. Trust/observability UX layer.

Verification:
1. Manual test on multiple cells and entities.

Exit Criteria:
1. Judges can inspect “why this value” instantly.

## Milestone 6 - Hardening, Docs, Submission
Goal: maximize evaluation score.

### Step 6.1 Test Pack and Benchmark Queries
Tasks:
1. Add 10-15 benchmark queries.
2. Define expected quality heuristics per query.
3. Add smoke benchmark script.

Deliverables:
1. `tests/benchmark_queries.json`.
2. Benchmark runner script.

Verification:
1. Run benchmark and record pass/fail observations.

Exit Criteria:
1. Consistent quality across representative topics.

### Step 6.2 Documentation and Architecture
Tasks:
1. Write complete README:
   - setup
   - design choices
   - trade-offs
   - limitations
   - future work
2. Add architecture diagram and request lifecycle.

Deliverables:
1. `README.md`
2. `docs/architecture.md` (+ image if used)

Verification:
1. Fresh setup test from docs.

Exit Criteria:
1. Another developer can run system with only README.

### Step 6.3 Demo Readiness
Tasks:
1. Prepare 3-minute demo flow.
2. Record backup demo video.
3. Validate final JSON export for one showcase query.

Deliverables:
1. Demo script and backup artifact.

Verification:
1. Full dry run without failures.

Exit Criteria:
1. Submission assets are complete and reliable.

## Implementation Order (Strict)
1. Milestone 0
2. Milestone 1
3. Milestone 2
4. Milestone 3
5. Milestone 4
6. Milestone 5
7. Milestone 6

## Per-Step Execution Template (Use Every Time)
1. Implement the smallest code slice.
2. Add/adjust tests for that slice.
3. Run verification commands.
4. Report pass/fail with evidence.
5. If fail: fix immediately before moving on.

## Suggested Verification Command Set
1. `pytest -q`
2. `ruff check .`
3. `mypy app`
4. `uvicorn app.main:app --reload` (manual API check)

## Risk Register (Active)
1. Search API quota/rate limits
   - Mitigation: provider abstraction + fallback.
2. Scraping failures on JS-heavy pages
   - Mitigation: multiple extraction strategies + partial success policy.
3. LLM schema drift
   - Mitigation: strict validation and retry with constrained prompt.
4. Latency spikes
   - Mitigation: caching + bounded page count + async fetching.

## Definition of Done
1. Required challenge features implemented.
2. Traceable evidence for each non-null value.
3. Quality controls (dedupe, scoring, validation) operational.
4. Clear docs and runnable setup.
5. Demo-ready flow and export output.

