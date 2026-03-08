from __future__ import annotations

import time
from typing import Generator

from .llm import OLLAMA_MODEL, generate_with_ollama, stream_with_ollama
from .rag import retrieve
from .tools import maybe_use_tools


SYSTEM_PROMPT = (
    "You are a privacy-first local assistant. Prefer retrieved local context, "
    "then tool outputs, and be explicit when information is uncertain. "
    "If the user asks to analyze provided docs, produce a short structured summary."
)


def _is_greeting(query: str) -> bool:
    q = query.strip().lower()
    return q in {"hi", "hello", "hey", "yo", "hola"}


def _compose_prompt(query: str, retrieved: list[dict], tool_outputs: list[dict]) -> str:
    context_blocks = []
    for i, c in enumerate(retrieved, start=1):
        context_blocks.append(
            f"[CTX {i}] source={c['source']} chunk={c['chunk_id']} score={c['score']}\n{c['text']}"
        )

    tool_blocks = []
    for t in tool_outputs:
        tool_blocks.append(f"[TOOL {t['tool']}] {t.get('result')}")

    context_text = "\n\n".join(context_blocks) if context_blocks else "No retrieved context"
    tools_text = "\n".join(tool_blocks) if tool_blocks else "No tool outputs"

    return (
        f"User query:\n{query}\n\n"
        f"Retrieved context:\n{context_text}\n\n"
        f"Tool outputs:\n{tools_text}\n\n"
        "Respond in this format:\n"
        "1) Direct answer (2-5 lines)\n"
        "2) Key points (3 bullets)\n"
        "3) Confidence (high/medium/low)\n"
        "Ground everything in the retrieved context/tool outputs. "
        "If evidence is missing, say so."
    )


def _context_fallback_summary(query: str, retrieved: list[dict]) -> str:
    if not retrieved:
        return "I could not find relevant indexed context. Upload more documents and try again."
    lines = [f"Local context summary for: {query}", ""]
    for i, item in enumerate(retrieved[:3], start=1):
        snippet = " ".join(item["text"].split())[:220]
        lines.append(f"{i}. [{item['source']} | score={item['score']}] {snippet}...")
    lines.append("")
    lines.append("Confidence: medium (context-based fallback, model generation unavailable).")
    return "\n".join(lines)


def run_query(query: str) -> dict:
    start = time.perf_counter()

    retrieved = retrieve(query=query, top_k=4)
    tool_trace, tool_outputs = maybe_use_tools(query)

    if _is_greeting(query) and not retrieved:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "answer": "Hello. Upload some documents and I will answer with grounded citations.",
            "citations": [],
            "tool_trace": tool_trace,
            "llm": {"provider": "ollama", "model": "qwen3.5:4b", "status": "skipped_greeting_fastpath"},
            "latency_ms": elapsed_ms,
        }

    prompt = _compose_prompt(query=query, retrieved=retrieved, tool_outputs=tool_outputs)
    answer, llm_meta = generate_with_ollama(prompt=prompt, system=SYSTEM_PROMPT)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    citations = [
        {
            "source": item["source"],
            "chunk_id": item["chunk_id"],
            "score": item["score"],
        }
        for item in retrieved
    ]

    if llm_meta.get("status") != "ok" and retrieved:
        preview = " ".join(c["text"][:140] for c in retrieved[:2])
        answer = f"Fallback answer from local context: {preview}"

    return {
        "answer": answer,
        "citations": citations,
        "tool_trace": tool_trace,
        "llm": llm_meta,
        "latency_ms": elapsed_ms,
    }


def stream_query(query: str) -> Generator[dict, None, None]:
    start = time.perf_counter()
    retrieved = retrieve(query=query, top_k=4)
    tool_trace, tool_outputs = maybe_use_tools(query)
    citations = [
        {
            "source": item["source"],
            "chunk_id": item["chunk_id"],
            "score": item["score"],
        }
        for item in retrieved
    ]

    yield {
        "type": "meta",
        "tool_trace": tool_trace,
        "citations": citations,
        "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": "starting"},
    }

    if _is_greeting(query) and not retrieved:
        answer = "Hello. Upload some documents and I will answer with grounded citations."
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        yield {"type": "token", "token": answer}
        yield {
            "type": "done",
            "answer": answer,
            "latency_ms": elapsed_ms,
            "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": "skipped_greeting_fastpath"},
        }
        return

    prompt = _compose_prompt(query=query, retrieved=retrieved, tool_outputs=tool_outputs)
    answer_parts: list[str] = []
    llm_status = "ok"

    for event in stream_with_ollama(prompt=prompt, system=SYSTEM_PROMPT):
        if event["type"] == "token":
            token = event["token"]
            answer_parts.append(token)
            yield {"type": "token", "token": token}
        elif event["type"] == "error":
            llm_status = "error"
            fallback = _context_fallback_summary(query, retrieved)
            answer_parts.append(fallback)
            yield {"type": "token", "token": fallback}
            break

    answer = "".join(answer_parts).strip()
    if not answer and retrieved:
        llm_status = "fallback_context_only"
        answer = _context_fallback_summary(query, retrieved)
        yield {"type": "token", "token": answer}

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    yield {
        "type": "done",
        "answer": answer,
        "latency_ms": elapsed_ms,
        "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": llm_status},
    }
