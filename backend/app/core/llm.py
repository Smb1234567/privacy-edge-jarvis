from __future__ import annotations

import os
from typing import Any

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")


def generate_with_ollama(prompt: str, system: str | None = None, timeout_s: int = 120) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }
    if system:
        payload["system"] = system

    try:
        res = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout_s,
        )
        res.raise_for_status()
        data = res.json()
        return data.get("response", ""), {"provider": "ollama", "model": OLLAMA_MODEL, "status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return (
            "Ollama unavailable. Returning context-grounded fallback response.",
            {"provider": "ollama", "model": OLLAMA_MODEL, "status": "error", "error": str(exc)},
        )
