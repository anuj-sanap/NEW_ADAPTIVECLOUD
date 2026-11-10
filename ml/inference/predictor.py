"""
ml/inference/predictor.py
Real-time flow predictor engine.
Loads active Isolation Forest anomaly detector and active multi-class classifier.
Returns {"status": "not_available"} honestly if models have not yet been trained or loaded.
Enforces validation on the 28 canonical flow features.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logger = logging.getLogger("flow_predictor")
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class FlowPredictor:
    """
    Inference coordinator executing two-stage detection:
    Stage 1: Isolation Forest unsupervised anomaly scoring
    Stage 2: Supervised attack classification with calibrated probabilities
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        self.models_dir = models_dir or MODELS_DIR
        self._anomaly_bundle: dict[str, Any] | None = None
        self._classifier_bundle: dict[str, Any] | None = None
        self._champion_name: str | None = None
        self.reload()

    def reload(self, classifier_name: str | None = None) -> None:
        """Reload models from disk, selecting specified or champion classifier."""
        self._anomaly_bundle = None
        self._classifier_bundle = None
        self._champion_name = classifier_name

        # 1. Load Isolation Forest
        iso_path = self.models_dir / "isolation_forest.joblib"
        if iso_path.exists():
            try:
                self._anomaly_bundle = joblib.load(iso_path)
                logger.info("Loaded Isolation Forest anomaly detector from %s", iso_path.name)
            except Exception as e:
                logger.error("Failed loading Isolation Forest: %s", e)

        # 2. Determine active classifier
        target_name = classifier_name
        if not target_name:
            comp_path = self.models_dir / "comparison.json"
            if comp_path.exists():
                try:
                    comp_data = json.loads(comp_path.read_text(encoding="utf-8"))
                    target_name = comp_data.get("best_model", "xgboost")
                except Exception:
                    target_name = "xgboost"
            else:
                target_name = "xgboost"

        clf_path = self.models_dir / f"{target_name}.joblib"
        if clf_path.exists():
            try:
                self._classifier_bundle = joblib.load(clf_path)
                self._champion_name = target_name
                logger.info("Loaded active classifier '%s' from %s", target_name, clf_path.name)
            except Exception as e:
                logger.error("Failed loading classifier '%s': %s", target_name, e)

    @property
    def is_anomaly_ready(self) -> bool:
        return self._anomaly_bundle is not None

    @property
    def is_classifier_ready(self) -> bool:
        return self._classifier_bundle is not None

    def _extract_feature_vector(self, features: dict[str, Any]) -> np.ndarray:
        validate_features(features, CANONICAL_FEATURES)
        vector = [float(features[f]) for f in CANONICAL_FEATURES]
        return np.array([vector], dtype=np.float64)

    def score_anomaly(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run unsupervised anomaly detection on a flow feature dictionary.
        Returns anomaly_score (0.0 to 1.0, where higher is more anomalous) and is_attack flag.
        """
        if not self.is_anomaly_ready:
            return {"status": "not_available"}

        try:
            X = self._extract_feature_vector(features)
            scaler = self._anomaly_bundle.get("scaler")
            if scaler is not None:
                X = scaler.transform(X)

            iso_model = self._anomaly_bundle["model"]
            # raw score_samples returns negative offset (e.g. -0.5 is anomalous, 0.0 is normal)
            raw_score = float(iso_model.score_samples(X)[0])
            # Normalize to 0.0-1.0 range (lower raw score -> higher anomaly score)
            # Typically raw_score is between -0.8 and 0.2
            normalized_score = float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0))

            prediction = int(iso_model.predict(X)[0])  # -1 for anomaly, 1 for inlier
            is_anomaly = bool(prediction == -1 or normalized_score >= 0.65)

            return {
                "status": "ok",
                "anomaly_score": round(normalized_score, 4),
                "is_attack": is_anomaly,
                "model_name": "isolation_forest",
                "model_version": self._anomaly_bundle.get("version", "1.0.0"),
            }
        except Exception as e:
            logger.error("Error during anomaly scoring: %s", e)
            return {"status": "error", "message": str(e)}

    def classify_attack(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Run multi-class supervised threat classification.
        Returns predicted label, confidence, and class probabilities dict.
        """
        if not self.is_classifier_ready:
            return {"status": "not_available"}

        try:
            X = self._extract_feature_vector(features)
            scaler = self._classifier_bundle.get("scaler")
            if scaler is not None:
                X = scaler.transform(X)

            clf = self._classifier_bundle["model"]
            le = self._classifier_bundle["label_encoder"]
            classes = list(le.classes_)

            pred_idx = int(clf.predict(X)[0])
            predicted_label = str(le.inverse_transform([pred_idx])[0])

            probs_dict: dict[str, float] = {}
            confidence = 1.0
            if hasattr(clf, "predict_proba"):
                probs = clf.predict_proba(X)[0]
                probs_dict = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
                confidence = float(probs[pred_idx])
            else:
                probs_dict = {predicted_label: 1.0}

            return {
                "status": "ok",
                "label": predicted_label,
                "confidence": round(confidence, 4),
                "probs": probs_dict,
                "model_name": self._champion_name or "classifier",
                "model_version": self._classifier_bundle.get("version", "1.0.0"),
            }
        except Exception as e:
            logger.error("Error during attack classification: %s", e)
            return {"status": "error", "message": str(e)}


flow_predictor = FlowPredictor()
