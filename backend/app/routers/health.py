from datetime import datetime, timezone

from fastapi import APIRouter

from ..core.llm import ollama_status
from ..core.rag import index_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp_utc": datetime.now(timezone.utc).isoformat()}


@router.get("/status")
def status() -> dict:
    return {
        "status": "ok",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "llm": ollama_status(),
        "index": index_status(),
    }
