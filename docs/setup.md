# Setup Guide

## 1) Backend
Follow `backend/README.md`.

## 2) Frontend
Phase 1 will add concrete install/run commands after scaffold.

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
