from __future__ import annotations

import json
import os
from typing import Any
from typing import Generator

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def ollama_status(timeout_s: int = 8) -> dict[str, Any]:
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=timeout_s)
        res.raise_for_status()
        data = res.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        return {
            "provider": "ollama",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
            "status": "ok" if any(OLLAMA_MODEL in m for m in models) else "model_missing",
            "available_models": models,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "ollama",
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
            "status": "unreachable",
            "error": str(exc),
        }


def generate_with_ollama(prompt: str, system: str | None = None, timeout_s: int = 45) -> tuple[str, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.2,
            "num_predict": 220,
            "think": False,
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


def stream_with_ollama(
    prompt: str,
    system: str | None = None,
    timeout_s: int = 90,
) -> Generator[dict[str, Any], None, None]:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.2,
            "num_predict": 220,
            "think": False,
        },
    }
    if system:
        payload["system"] = system

    try:
        with requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout_s,
            stream=True,
        ) as res:
            res.raise_for_status()
            for line in res.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = obj.get("response", "")
                if token:
                    yield {"type": "token", "token": token}
                if obj.get("done"):
                    yield {"type": "done_meta", "raw": obj}
                    break
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "error": str(exc)}
