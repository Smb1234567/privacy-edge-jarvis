import time

from .tools import maybe_use_tools


def run_query(query: str) -> dict:
    start = time.perf_counter()
    tool_trace = maybe_use_tools(query)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    # Placeholder generation path; wire Ollama + RAG retrieval in Phase 1 implementation.
    answer = f"MVP response placeholder for query: {query}"

    return {
        "answer": answer,
        "citations": [],
        "tool_trace": tool_trace,
        "latency_ms": elapsed_ms,
    }
