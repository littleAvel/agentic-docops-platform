from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.ui.routes_ui import router as ui_router


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Document Ops Platform", version="0.1.0")

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(ui_router)

    return app


app = create_app()
