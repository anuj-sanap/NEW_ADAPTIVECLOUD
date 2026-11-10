"""
backend/app/main.py
FastAPI application entry point.
Configures CORS, custom global error envelope {error: {code, message}},
health monitoring with database ping, and mounts all API v1 and WebSocket routes.
"""
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import AsyncGenerator

# Ensure repository root is on sys.path for ml and agent imports
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes import (
    agent_ingest,
    auth,
    classifications,
    detections,
    events,
    hosts,
    incidents,
    ingest,
    models,
)
from app.api.v1.routes.stubs import (
    audit_router,
    dashboard_router,
    learning_router,
    metrics_router,
    rca_router,
    reports_router,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine, get_db
from app.services.wazuh_ingestor import wazuh_tailer
from app.websocket.router import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger = get_logger("startup")
    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    # Start background Wazuh alert tailer worker
    wazuh_tailer.start()
    yield
    await wazuh_tailer.stop()
    await engine.dispose()
    logger.info("Application shutdown and DB pool disposed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── Global Error Handling: { error: { code, message } } ──────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "CONFLICT"
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"
    elif exc.status_code == 501:
        code = "NOT_IMPLEMENTED"

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "; ".join([f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in errors])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "VALIDATION_ERROR", "message": message}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = get_logger("exception")
    logger.error("Unhandled server exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An internal server error occurred"}},
    )


# ── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["health"], summary="Liveness & DB Readiness Check")
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger = get_logger("health")
        logger.error("Database healthcheck probe failed", error=str(e))
        db_status = "error"

    status_code = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_status == "ok" else "degraded",
            "version": settings.APP_VERSION,
            "db": db_status,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


# ── Route Mounting ───────────────────────────────────────────────────────────
v1 = settings.API_V1_PREFIX

# Core implemented routes
app.include_router(auth.router, prefix=v1)
app.include_router(ingest.router, prefix=v1)
app.include_router(agent_ingest.router, prefix=v1)
app.include_router(hosts.router, prefix=v1)
app.include_router(events.router, prefix=v1)
app.include_router(detections.router, prefix=v1)
app.include_router(classifications.router, prefix=v1)
app.include_router(incidents.router, prefix=v1)
app.include_router(models.router, prefix=v1)

# Route groups (stubs returning 501 until implemented)
app.include_router(metrics_router, prefix=v1)
app.include_router(rca_router, prefix=v1)
app.include_router(learning_router, prefix=v1)
app.include_router(reports_router, prefix=v1)
app.include_router(audit_router, prefix=v1)
app.include_router(dashboard_router, prefix=v1)

# WebSocket streaming hub
app.include_router(ws_router)
