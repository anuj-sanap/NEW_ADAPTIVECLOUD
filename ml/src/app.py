"""
ml/src/app.py
FastAPI ML microservice — exposes /predict, /train, /status.
Runs internally on port 8001 (not exposed to internet/Nginx directly).
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ml-service")

# ── Lazy import heavy deps after startup ─────────────────────────────────────
predictor_instance = None
_training_status: dict[str, Any] = {"job_status": "idle"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global predictor_instance
    from predictor import Predictor
    predictor_instance = Predictor()
    logger.info("ML service ready | model_ready=%s", predictor_instance.is_ready())
    yield


app = FastAPI(title="Adaptive Cloud ML Service", version="1.0.0", lifespan=lifespan)


# ── Request / Response schemas ───────────────────────────────────────────────

class PredictRequest(BaseModel):
    metric_id: str
    features: dict[str, Any]  # Raw MetricPayload dict


class TrainRequest(BaseModel):
    job_id: str


class PredictResponse(BaseModel):
    metric_id: str
    label: str
    confidence: float
    model_version: str
    features_used: list[str]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/predict")
async def predict(req: PredictRequest) -> JSONResponse:
    """Run inference on a single MetricPayload and return classification result."""
    if predictor_instance is None:
        return JSONResponse({"status": "not_available"}, status_code=503)

    result = predictor_instance.predict(req.features)
    if result.get("status") == "not_available":
        return JSONResponse({"status": "not_available"}, status_code=503)

    return JSONResponse({
        "metric_id": req.metric_id,
        **result,
    })


@app.post("/train", status_code=202)
async def train(req: TrainRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Trigger model retraining in the background.
    The backend must POST labelled data to this endpoint.
    In Phase 2, we will add a data-fetching step here.
    """
    global _training_status

    if _training_status.get("job_status") == "training":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A training job is already running.",
        )

    _training_status = {"job_status": "queued", "job_id": req.job_id}

    async def _run_training() -> None:
        global _training_status
        _training_status["job_status"] = "training"
        try:
            # Import here so the module loads after lifespan
            from trainer import InsufficientDataError

            # TODO Phase 2: fetch labelled data from backend DB via REST
            # For now, we raise InsufficientDataError cleanly
            raise InsufficientDataError(
                "No labelled data available yet. Collect metrics and label them first."
            )
        except InsufficientDataError as exc:
            logger.warning("Training skipped: %s", exc)
            _training_status = {
                "job_status": "failed",
                "error": str(exc),
                "job_id": req.job_id,
            }
        except Exception as exc:
            logger.error("Training failed: %s", exc, exc_info=True)
            _training_status = {
                "job_status": "failed",
                "error": str(exc),
                "job_id": req.job_id,
            }
        else:
            _training_status["job_status"] = "idle"
            if predictor_instance:
                predictor_instance.reload()

    background_tasks.add_task(_run_training)
    return JSONResponse({"job_id": req.job_id, "status": "queued"})


@app.get("/status")
async def status_check() -> JSONResponse:
    """Return current model status."""
    if predictor_instance is None:
        return JSONResponse({"status": "not_available"})

    model_status = predictor_instance.status()
    # Merge live training job status
    model_status["job_status"] = _training_status.get("job_status", "idle")
    return JSONResponse(model_status)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "model_ready": predictor_instance.is_ready() if predictor_instance else False,
        "timestamp": datetime.now(UTC).isoformat(),
    })

