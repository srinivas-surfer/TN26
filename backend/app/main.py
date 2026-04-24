"""
TN2026 Election Intelligence System — FastAPI Backend
Optimized for t2.micro: single worker, async I/O, aggressive caching.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.utils.logger import setup_logging
from app.utils.db import setup_indexes, close_client
from app.utils.cache import get_cache_stats
from app.api import trends, prediction, constituency, region, live
from app.pipeline.scheduler import start_scheduler, stop_scheduler

setup_logging()
logger = logging.getLogger("tn2026.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("TN2026 backend starting up...")
    await setup_indexes()
    await start_scheduler()
    yield
    logger.info("TN2026 backend shutting down...")
    stop_scheduler()
    await close_client()


app = FastAPI(
    title="TN2026 Election Intelligence API",
    description="Tamil Nadu 2026 Assembly Election — Poll Aggregator & ML Predictor",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,  # save memory
)

# CORS — restrict to frontend origin in production
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Routers ──────────────────────────────────────────────
app.include_router(trends.router, tags=["Trends"])
app.include_router(prediction.router, tags=["Predictions"])
app.include_router(constituency.router, tags=["Constituencies"])
app.include_router(region.router, tags=["Regions"])
app.include_router(live.router, tags=["Live"])


# ── Health & Meta ─────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "service": "tn2026-backend"}


@app.get("/cache/stats", tags=["Meta"])
async def cache_stats():
    return get_cache_stats()


@app.get("/", tags=["Meta"])
async def root():
    return {
        "service": "TN2026 Election Intelligence API",
        "version": "1.0.0",
        "endpoints": [
            "/trends", "/prediction", "/constituencies",
            "/constituency/{id}", "/region/{name}", "/live-results",
            "/health", "/docs",
        ],
    }


# ── Global error handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
