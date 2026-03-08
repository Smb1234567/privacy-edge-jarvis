from duckduckgo_search import DDGS


def list_tools() -> list[str]:
    return [
        "local_file_search",
        "duckduckgo_web_search",
        "sqlite_query",
        "calculator",
    ]


def maybe_use_tools(query: str) -> list[dict]:
    trace = []
    q = query.lower()

    if "search web" in q or "latest" in q or "news" in q:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        trace.append(
            {
                "tool": "duckduckgo_web_search",
                "status": "ok",
                "results": [r.get("title", "") for r in results],
            }
        )

    if any(token in q for token in ["calculate", "+", "-", "*", "/"]):
        trace.append({"tool": "calculator", "status": "stub"})

    if not trace:
        trace.append({"tool": "local_file_search", "status": "stub"})

    return trace
