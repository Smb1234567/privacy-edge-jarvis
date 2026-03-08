from fastapi import APIRouter
from pydantic import BaseModel

from ..core.orchestrator import run_query

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    return run_query(req.query)
