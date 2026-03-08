from __future__ import annotations

import ast
import operator
import sqlite3
from pathlib import Path

from duckduckgo_search import DDGS

from .rag import BASE_DIR, search_local

DB_PATH = BASE_DIR / "data" / "processed" / "assistant.db"


def list_tools() -> list[str]:
    return [
        "local_file_search",
        "duckduckgo_web_search",
        "sqlite_query",
        "calculator",
    ]


def _safe_calc(expr: str) -> float:
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](eval_node(node.left), eval_node(node.right))
        raise ValueError("Unsupported expression")

    parsed = ast.parse(expr, mode="eval")
    return round(eval_node(parsed.body), 6)


def _run_sql(query: str) -> list[tuple]:
    q = query.strip().lower()
    if not q.startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchmany(20)
        return rows
    finally:
        conn.close()


def maybe_use_tools(query: str) -> tuple[list[dict], list[dict]]:
    trace: list[dict] = []
    outputs: list[dict] = []
    q = query.lower()

    # Always run local retrieval as the primary private-memory tool.
    local_hits = search_local(query, top_k=3)
    trace.append({"tool": "local_file_search", "status": "ok", "hits": len(local_hits)})
    outputs.append({"tool": "local_file_search", "result": local_hits})

    if any(k in q for k in ["search web", "web", "latest", "news", "online"]):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            reduced = [{"title": r.get("title", ""), "href": r.get("href", "")} for r in results]
            trace.append({"tool": "duckduckgo_web_search", "status": "ok", "hits": len(reduced)})
            outputs.append({"tool": "duckduckgo_web_search", "result": reduced})
        except Exception as exc:  # noqa: BLE001
            trace.append({"tool": "duckduckgo_web_search", "status": "error", "error": str(exc)})

    if "calculate" in q or "math" in q:
        expr = query.split(":", 1)[-1].strip() if ":" in query else ""
        if expr:
            try:
                val = _safe_calc(expr)
                trace.append({"tool": "calculator", "status": "ok"})
                outputs.append({"tool": "calculator", "result": val, "expression": expr})
            except Exception as exc:  # noqa: BLE001
                trace.append({"tool": "calculator", "status": "error", "error": str(exc)})

    if q.startswith("sql:"):
        sql = query[4:].strip()
        try:
            rows = _run_sql(sql)
            trace.append({"tool": "sqlite_query", "status": "ok", "rows": len(rows)})
            outputs.append({"tool": "sqlite_query", "result": rows})
        except Exception as exc:  # noqa: BLE001
            trace.append({"tool": "sqlite_query", "status": "error", "error": str(exc)})

    return trace, outputs
