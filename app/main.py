import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.models.schemas import SearchRequest, SearchResponse
from app.services.dedupe import EntityDeduper
from app.services.evidence_validator import EvidenceValidator
from app.services.extractor import EntityExtractor, StructuredLLMClient
from app.services.openai_client import get_structured_llm_client
from app.services.pipeline import SearchPipeline
from app.services.scoring import ConfidenceScorer
from app.services.scraper import WebScraper
from app.services.search_client import SearchClient, SerpAPISearchProvider
from app.storage.page_cache import PageCache
from app.storage.run_store import RunStore


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


class NullStructuredLLMClient(StructuredLLMClient):
    """Fallback LLM adapter used when OpenAI credentials are unavailable."""

    def complete(self, prompt: str, schema: dict) -> dict:
        return {"entities": []}


def get_extractor_client() -> StructuredLLMClient:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    if provider == "openai" and not api_key:
        return NullStructuredLLMClient()
    if provider == "groq" and not groq_key:
        return NullStructuredLLMClient()

    try:
        return get_structured_llm_client()
    except Exception:
        # Keep API operational even when model client initialization fails.
        return NullStructuredLLMClient()


app = FastAPI(title="Agentic Search Challenge API", version="0.1.0")


_UI_HTML = (Path(__file__).parent / "ui" / "index.html").read_text(encoding="utf-8")
_run_store = RunStore()


def get_pipeline() -> SearchPipeline:
    return SearchPipeline(
        search_client=SearchClient(provider=SerpAPISearchProvider()),
        scraper=WebScraper(),
        extractor=EntityExtractor(client=get_extractor_client()),
        evidence_validator=EvidenceValidator(),
        deduper=EntityDeduper(),
        scorer=ConfidenceScorer(),
        cache=PageCache(),
    )


def get_run_store() -> RunStore:
    return _run_store


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _UI_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    pipeline: SearchPipeline = Depends(get_pipeline),
    run_store: RunStore = Depends(get_run_store),
) -> SearchResponse:
    result = pipeline.run(query=payload.query, max_results=payload.max_results)
    run_store.save(query=payload.query, result=result)
    return result


@app.get("/runs/{run_id}", response_model=SearchResponse)
def get_run(run_id: str, run_store: RunStore = Depends(get_run_store)) -> SearchResponse:
    result = run_store.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="run not found")
    return result


@app.get("/export/{run_id}.json")
def export_run(run_id: str, run_store: RunStore = Depends(get_run_store)) -> dict:
    payload = run_store.export_payload(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    return payload
