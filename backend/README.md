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
- `GET /api/tools`
- `GET /api/benchmark/metrics`
