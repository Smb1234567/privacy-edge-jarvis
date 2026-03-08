# Setup Guide

## 1) Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Shortcut:
```bash
./scripts/run_backend.sh
```

## 2) Frontend
Open `http://127.0.0.1:8000` in your browser.

## 3) Local model
- Ensure Ollama is running.
- Pull and run `qwen3.5:4b`.
```bash
ollama pull qwen3.5:4b
ollama run qwen3.5:4b
```

## 4) Data
Place local docs in `data/raw/` and trigger reindex:
```bash
curl -X POST http://127.0.0.1:8000/api/ingest/reindex
```

Or upload docs directly:
```bash
curl -X POST http://127.0.0.1:8000/api/ingest \
  -F "files=@/path/to/file1.pdf" \
  -F "files=@/path/to/file2.md"
```
