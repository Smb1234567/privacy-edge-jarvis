# Backend (FastAPI)

## Run locally
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints
- `GET /api/health`
- `POST /api/chat`
- `POST /api/ingest`
- `POST /api/ingest/reindex`
- `GET /api/tools`
- `GET /api/benchmark/metrics`

## Query conventions (MVP)
- Web lookup: include `web` or `latest` in query
- Calculator: `calculate: 12*(4+1)`
- SQLite: `sql: SELECT name FROM sqlite_master;`
