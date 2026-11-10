"""
ml/src/predictor.py
Loads the active model and runs inference on a MetricPayload dict.
Returns {"status": "not_available"} if no model is loaded.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from features import FEATURE_NAMES, LABEL_CLASSES, extract_features

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"


class Predictor:
    """
    Loads the latest trained model and provides single-sample inference.

    Thread-safe for read access after initial load.
    Call reload() to pick up a newly trained model without restarting.
    """

    def __init__(self) -> None:
        self._model = None
        self._label_encoder = None
        self._meta: dict[str, Any] = {}
        self._load_latest()

    def _load_latest(self) -> None:
        """Find and load the most recently created model artefact."""
        model_files = sorted(MODELS_DIR.glob("model_v*.joblib"))
        if not model_files:
            logger.warning("No trained model found in %s", MODELS_DIR)
            return

        latest = model_files[-1]
        meta_path = latest.with_suffix("").with_suffix("").parent / (latest.stem + "_meta.json")

        try:
            artefact = joblib.load(latest)
            self._model = artefact["model"]
            self._label_encoder = artefact["label_encoder"]

            if meta_path.exists():
                self._meta = json.loads(meta_path.read_text())
            else:
                self._meta = {"version": latest.stem.replace("model_", "")}

            logger.info("Model loaded | version=%s", self._meta.get("version"))
        except Exception as exc:
            logger.error("Failed to load model %s: %s", latest, exc)

    def reload(self) -> None:
        """Reload the model from disk (call after a new training run completes)."""
        self._model = None
        self._label_encoder = None
        self._meta = {}
        self._load_latest()

    def is_ready(self) -> bool:
        """True if a model is loaded and ready for inference."""
        return self._model is not None

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Run inference on a MetricPayload dict.

        Returns:
            Dict with keys: label, confidence, model_version, features_used.
            Or: {"status": "not_available"} if no model is loaded.
        """
        if not self.is_ready():
            return {"status": "not_available"}

        try:
            features = extract_features(payload)
            X = features.reshape(1, -1)

            # Probability vector for all classes
            proba = self._model.predict_proba(X)[0]  # shape: (n_classes,)
            pred_idx = int(np.argmax(proba))
            confidence = float(proba[pred_idx])
            label = self._label_encoder.inverse_transform([pred_idx])[0]

            return {
                "label": label,
                "confidence": round(confidence, 4),
                "model_version": self._meta.get("version", "unknown"),
                "features_used": FEATURE_NAMES,
            }
        except Exception as exc:
            logger.error("Inference error: %s", exc, exc_info=True)
            return {"status": "not_available", "error": str(exc)}

    def status(self) -> dict[str, Any]:
        """Return the current model status (mirrors GET /ml/status schema)."""
        if not self.is_ready():
            return {"status": "not_available"}

        return {
            "status": "ready",
            "model_version": self._meta.get("version"),
            "trained_at": self._meta.get("trained_at"),
            "training_samples": self._meta.get("training_samples"),
            "features": self._meta.get("feature_names", FEATURE_NAMES),
            "labels": self._meta.get("label_classes", LABEL_CLASSES),
            "job_status": "idle",
        }
