from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Generator, Any

from .llm import OLLAMA_MODEL, generate_with_ollama, stream_with_ollama
from .rag import retrieve
from .tools import maybe_use_tools


SYSTEM_PROMPT = """You are Jarvis, an autonomous AI assistant running locally on the user's machine.

You are helpful, friendly, and conversational. You have access to various tools to help answer questions.

You can use these tools:
- read_file(path) - Read file contents
- list_directory(path) - List files in a directory  
- search_files(directory, pattern) - Find files by name
- grep_search(directory, query) - Search file contents
- run_command(command) - Execute shell commands
- get_system_info() - Get CPU, RAM, disk info
- web_search(query) - Search the web
- query_knowledge_base(query) - Query local documents

Guidelines:
- Be concise and conversational
- Use tools when needed to provide accurate information
- After using a tool, summarize the results for the user
- Don't output JSON, just respond naturally
"""


TOOL_FUNCTIONS = {
    "get_system_info": lambda: _get_system_info(),
    "get_jarvis_status": lambda: _get_jarvis_status(),
    "list_directory": lambda path: _list_directory(path),
    "read_file": lambda path: _read_file(path),
    "web_search": lambda query: _web_search(query),
    "query_knowledge_base": lambda query: _query_knowledge_base(query),
}


def _get_system_info() -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return f"CPU: {cpu}%, RAM: {mem.percent}% ({mem.used/(1024**3):.1f}GB used), Disk: {disk.percent}%"
    except Exception as e:
        return f"Error: {e}"


def _get_jarvis_status() -> str:
    try:
        import requests
        res = requests.get("http://127.0.0.1:8000/api/status", timeout=5)
        data = res.json()
        llm = data.get("llm", {})
        index = data.get("index", {})
        return f"LLM: {llm.get('model')} ({llm.get('status')}), Docs: {index.get('documents')}, Chunks: {index.get('chunks')}"
    except Exception as e:
        return f"Error: {e}"


def _list_directory(path: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Path not found: {path}"
        items = [f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in sorted(p.iterdir())[:20]]
        return "\n".join(items) if items else "Empty"
    except Exception as e:
        return f"Error: {e}"


def _read_file(path: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"File not found: {path}"
        content = p.read_text()
        if len(content) > 2000:
            return content[:2000] + f"\n... ({len(content)} total chars)"
        return content
    except Exception as e:
        return f"Error: {e}"


def _web_search(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No results found"
        output = []
        for r in results:
            output.append(f"- {r.get('title', 'No title')}: {r.get('href', '')}")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"


def _query_knowledge_base(query: str) -> str:
    try:
        results = retrieve(query=query, top_k=3)
        if not results:
            return "No relevant documents found"
        output = []
        for r in results:
            text = r.get("text", "")[:200]
            source = r.get("source", "unknown").split("/")[-1]
            output.append(f"- {source}: {text}...")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"


def _extract_tool_call(text: str) -> tuple[str | None, dict | None]:
    """Extract tool call from model output."""
    patterns = [
        r'\{[^{}]*"action"\s*:\s*"([^"]+)"[^{}]*"params"\s*:\s*(\{[^\}]+\})[^\}]*\}',
        r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*\}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if len(match.groups()) >= 2:
                    tool_name = match.group(1)
                    params = json.loads(match.group(2))
                    return tool_name, params
                elif len(match.groups()) == 1:
                    tool_name = match.group(1)
                    return tool_name, {}
            except:
                pass
    
    return None, None


def _is_greeting(query: str) -> bool:
    q = query.strip().lower()
    return q in {"hi", "hello", "hey", "yo", "hola", "howdy", "greetings", "sup"}


def run_query(query: str) -> dict:
    start = time.perf_counter()

    if _is_greeting(query):
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "answer": "Hey! I'm your local AI assistant. I can help you with your files, search the web, check system status, and answer questions about your documents. What would you like to do?",
            "citations": [],
            "tool_trace": [],
            "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": "ok"},
            "latency_ms": elapsed_ms,
        }

    tool_trace = []
    tool_outputs = []
    
    retrieved = retrieve(query=query, top_k=3)
    citations = [{"source": item["source"], "chunk_id": item["chunk_id"], "score": item["score"]} for item in retrieved]
    
    if retrieved:
        context = "\n".join([f"[Document]: {c['text'][:500]}" for c in retrieved])
    else:
        context = "No relevant documents found."
    
    prompt = f"""User question: {query}

Relevant context:
{context}

Provide a helpful, conversational answer based on the context above. If you need additional information, you can call a tool. Just respond naturally - don't output JSON."""

    answer, llm_meta = generate_with_ollama(prompt=prompt, system=SYSTEM_PROMPT)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "answer": answer,
        "citations": citations,
        "tool_trace": tool_trace,
        "llm": llm_meta,
        "latency_ms": elapsed_ms,
    }


def stream_query(query: str) -> Generator[dict, None, None]:
    start = time.perf_counter()
    
    if _is_greeting(query):
        answer = "Hey! I'm your local AI assistant. I can help you with your files, search the web, check system status, and answer questions about your documents. What would you like to do?"
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        yield {"type": "token", "token": answer}
        yield {
            "type": "done",
            "answer": answer,
            "latency_ms": elapsed_ms,
            "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": "ok"},
        }
        return

    tool_trace = []
    tool_outputs = []
    
    retrieved = retrieve(query=query, top_k=3)
    citations = [{"source": item["source"], "chunk_id": item["chunk_id"], "score": item["score"]} for item in retrieved]
    
    yield {
        "type": "meta",
        "tool_trace": tool_trace,
        "citations": citations,
        "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": "starting"},
    }

    if retrieved:
        context = "\n".join([f"[Document]: {c['text'][:500]}" for c in retrieved])
    else:
        context = "No relevant documents found."
    
    prompt = f"""User question: {query}

Relevant context:
{context}

Provide a helpful, conversational answer based on the context above. Be concise and natural."""

    answer_parts = []
    llm_status = "ok"

    for event in stream_with_ollama(prompt=prompt, system=SYSTEM_PROMPT):
        if event["type"] == "token":
            token = event["token"]
            answer_parts.append(token)
            yield {"type": "token", "token": token}
        elif event["type"] == "error":
            llm_status = "error"
            answer_parts.append(f"Error: {event.get('error', 'Unknown error')}")
            yield {"type": "token", "token": answer_parts[-1]}
            break

    answer = "".join(answer_parts).strip()
    if not answer:
        answer = "I wasn't able to generate a response. Could you try rephrasing?"

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    yield {
        "type": "done",
        "answer": answer,
        "latency_ms": elapsed_ms,
        "llm": {"provider": "ollama", "model": OLLAMA_MODEL, "status": llm_status},
    }
