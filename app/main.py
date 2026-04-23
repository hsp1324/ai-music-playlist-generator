from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_db
from app.routes import health, playlists, slack, suno, tracks, ui, youtube
from app.services import build_service_registry


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_storage_dirs()
    init_db()
    services = build_service_registry(settings)
    static_dir = Path(__file__).resolve().parent / "static"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.services = services

    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")
    app.mount("/media", StaticFiles(directory=settings.storage_root), name="media")

    app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(tracks.router, prefix=settings.api_prefix)
    app.include_router(suno.router, prefix=settings.api_prefix)
    app.include_router(playlists.router, prefix=settings.api_prefix)
    app.include_router(slack.router, prefix=settings.api_prefix)
    app.include_router(youtube.router, prefix=settings.api_prefix)
    return app


app = create_app()
