"""
backend/app/main.py
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import agents, auth, ingest, metrics, predictions
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.websocket.router import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle hooks."""
    configure_logging()
    logger = get_logger("startup")
    logger.info(
        "Starting up",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.ENVIRONMENT,
    )
    yield
    # Dispose DB connection pool on shutdown
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ───────────────────────────────────────────────────────────────
API_PREFIX = settings.API_V1_PREFIX

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(metrics.router, prefix=API_PREFIX)
app.include_router(predictions.router, prefix=API_PREFIX)

# ── WebSocket ─────────────────────────────────────────────────────────────────
app.include_router(ws_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["health"], summary="Liveness + readiness check")
async def health() -> JSONResponse:
    """
    Public health endpoint.
    Checks DB connectivity by running a lightweight query.
    """
    db_status = "ok"
    try:
        from sqlalchemy import text
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    http_status = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ok" if db_status == "ok" else "degraded",
            "version": settings.APP_VERSION,
            "db": db_status,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
