from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    return app


app = create_app()
