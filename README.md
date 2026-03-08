# Privacy-Preserving Agentic RAG with MCP on Edge Hardware

Offline-first local AI assistant focused on privacy, tool orchestration, and measurable performance on constrained hardware (RTX 3050 6GB, Ryzen 5 8645HS, 16GB RAM).

## MVP Goal
Build a local "Jarvis" assistant that can:
- Answer from local knowledge base (RAG)
- Use MCP tools (file search, web search, calculator, SQLite query)
- Chain multiple tools when needed
- Show citations + tool trace + latency/resource metrics

## Hardware-First Constraints (Research Variable)
- GPU: RTX 3050 6GB VRAM
- CPU: Ryzen 5 8645HS
- RAM: 16GB
- Local LLM: `qwen3.5:4b` via Ollama

## Phase Roadmap
- Phase 0: Research framing + hypotheses
- Phase 1: MVP core (RAG + MCP tools + simple UI)
- Phase 2: Agentic chaining + observability
- Phase 3: Benchmark suite + ablations
- Phase 4: Publication package (figures, table templates, reproducibility)

## Monorepo Structure
- `backend/` FastAPI + orchestration + ingestion + evaluation hooks
- `frontend/` modern chat UI (Next.js)
- `benchmarks/` reproducible benchmark scripts and configs
- `docs/` architecture, experiment plans, paper outline
- `configs/` model/tool/index settings

## Quick Start (MVP)
1. Create python env and install backend deps.
2. Start backend API (`uvicorn app.main:app --reload --port 8000` from `backend/`).
3. Open frontend UI at `http://127.0.0.1:8000`.
4. Load docs into index via ingestion endpoint.

Detailed setup is in `docs/setup.md`.
