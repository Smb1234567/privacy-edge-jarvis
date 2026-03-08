from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .routers import health, chat, ingest, tools, benchmark


def create_app() -> FastAPI:
    app = FastAPI(title="Privacy Edge Jarvis API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(ingest.router, prefix="/api")
    app.include_router(tools.router, prefix="/api")
    app.include_router(benchmark.router, prefix="/api")

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def serve_ui() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()
