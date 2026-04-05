"""FastAPI application factory and lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cliptrans.adapters.persistence.database import create_tables
from cliptrans.config import get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    await create_tables(cfg.database_url)
    yield


def create_app() -> FastAPI:
    from pathlib import Path

    from cliptrans.entrypoints.api.routes import clips, pages, streams

    app = FastAPI(title="ClipTrans Web UI", lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(pages.router)
    app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
    app.include_router(clips.router, prefix="/api/clips", tags=["clips"])

    return app


app = create_app()


def main() -> None:
    import uvicorn

    cfg = get_config()
    uvicorn.run(
        "cliptrans.entrypoints.api.app:app",
        host=cfg.web_host,
        port=cfg.web_port,
        reload=False,
    )
