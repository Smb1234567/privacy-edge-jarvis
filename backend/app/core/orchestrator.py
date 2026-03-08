from __future__ import annotations

import time

from .llm import generate_with_ollama
from .rag import retrieve
from .tools import maybe_use_tools


SYSTEM_PROMPT = (
    "You are a privacy-first local assistant. Prefer retrieved local context, "
    "then tool outputs, and be explicit when information is uncertain."
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
        "Answer with concise reasoning grounded in the context/tool outputs. "
        "If evidence is missing, say so."
    )


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
