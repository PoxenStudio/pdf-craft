"""
FastAPI application factory and entry point.

Run with:
    python -m server.main
or directly:
    python server/main.py
"""

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.cleanup import start_cleanup_scheduler
from server.config import DATA_DIR, SERVER_HOST, SERVER_PORT
from server.routes import settings_router, tasks_router
from server.settings_store import (
    settings_store as _settings_store,
)  # noqa: F401 – initialises singleton
from server.task_store import task_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PoxenStudio PDF Craft",
    description="HTTP API for converting PDF documents to EPUB using AI-powered OCR.",
    version="1.0.0",
)

# Register API routes
app.include_router(tasks_router)
app.include_router(settings_router)

# Serve static files (Web UI)
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the single-page Web UI."""
    return FileResponse(str(_static_dir / "index.html"))


# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    start_cleanup_scheduler(task_store)
    logger.info("Server started. Data directory: %s", DATA_DIR)


# ---------------------------------------------------------------------------
# Development entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
    )
