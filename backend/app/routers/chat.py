from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

import json

from ..core.orchestrator import run_query, stream_query

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    return run_query(req.query)


@router.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    def event_lines():
        for event in stream_query(req.query):
            yield json.dumps(event, ensure_ascii=True) + "\n"

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")
