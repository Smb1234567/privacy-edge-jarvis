import os

API_HOST = os.getenv("API_HOST", "http://127.0.0.1:8000")
API_BASE = f"{API_HOST}/api"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

MAX_RETRIES = 3
RETRY_DELAY = 1.0
