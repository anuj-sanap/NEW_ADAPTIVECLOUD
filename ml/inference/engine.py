"""
ml/inference/engine.py
Production Two-Stage Threat Inference Engine.
Stage 1: Unsupervised Outlier/Anomaly Detection.
Stage 2: Supervised Multi-Class Classification.
HONESTY RULES:
- No active model -> {"status": "not_available"}.
- Low confidence or out-of-distribution patterns are labelled "unknown_suspicious",
  NEVER forced into a known attack class.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import joblib
import numpy as np

from ml.features.spaces import get_feature_space
from ml.taxonomy.labels import AttackFamily

logger = logging.getLogger("ml.inference.engine")
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class InferenceEngine:
    """
    Two-stage inference engine implementing AdaptiveCloud honesty rules.
    """

    def __init__(
        self,
        feature_space: str = "FS-CIC",
        models_dir: Optional[Path] = None,
        confidence_threshold: float = 0.50,
    ) -> None:
        self.feature_space = feature_space
        self.models_dir = models_dir or MODELS_DIR
        self.confidence_threshold = confidence_threshold
        self._space_def = get_feature_space(feature_space)

        self._anomaly_detector = None
        self._classifier_bundle: Optional[Dict[str, Any]] = None
        self._active_model_name: Optional[str] = None
        self.reload()

    def reload(self, model_name: Optional[str] = None) -> None:
        """Loads models from disk matching feature space."""
        self._anomaly_detector = None
        self._classifier_bundle = None

        # 1. Load Anomaly Detector
        ano_path = self.models_dir / f"isolation_forest_{self.feature_space.lower()}.joblib"
        if not ano_path.exists():
            ano_path = self.models_dir / "isolation_forest.joblib"
        if ano_path.exists():
            try:
                self._anomaly_detector = joblib.load(ano_path)
                logger.info("Loaded anomaly detector from %s", ano_path.name)
            except Exception as e:
                logger.error("Failed loading anomaly detector: %s", e)

        # 2. Determine Classifier
        target = model_name
        if not target:
            # Check comparison.json for champion
            comp_file = self.models_dir / "comparison.json"
            if comp_file.exists():
                try:
                    cdata = json.loads(comp_file.read_text(encoding="utf-8"))
                    target = cdata.get("champion_candidate", cdata.get("best_model"))
                except Exception:
                    pass
        if not target:
            # Fallback to feature-space specific or standard classifiers
            candidates = [
                f"xgboost_{self.feature_space.lower()}",
                f"random_forest_{self.feature_space.lower()}",
                f"lightgbm_{self.feature_space.lower()}",
                "xgboost",
                "random_forest",
                "lightgbm",
            ]
            for candidate in candidates:
                if (self.models_dir / f"{candidate}.joblib").exists():
                    target = candidate
                    break

        if not target:
            # Check for any .joblib in models_dir
            any_joblibs = list(self.models_dir.glob("*.joblib"))
            for jf in any_joblibs:
                if "isolation_forest" not in jf.stem and "maintenance" not in jf.stem and "threat_forecast" not in jf.stem:
                    target = jf.stem
                    break

        if target:
            clf_path = self.models_dir / f"{target}.joblib"
            if clf_path.exists():
                try:
                    self._classifier_bundle = joblib.load(clf_path)
                    self._active_model_name = target
                    logger.info("Loaded active classifier '%s' from %s", target, clf_path.name)
                except Exception as e:
                    logger.error("Failed loading classifier '%s': %s", target, e)

    @property
    def is_ready(self) -> bool:
        """Returns True if at least classifier or anomaly detector is ready."""
        return self._classifier_bundle is not None

    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes two-stage threat detection.
        Returns prediction details or {"status": "not_available"}.
        """
        if not self.is_ready:
            return {
                "status": "not_available",
                "message": "No active threat detection model loaded",
            }

        try:
            bundle = self._classifier_bundle
            clf = bundle["model"]
            extractor = bundle.get("extractor")
            scaler = bundle.get("scaler")
            le = bundle["label_encoder"]
            classes = list(le.classes_)

            # Extract feature vector
            if extractor is not None:
                X = extractor.transform_dict(record)
            else:
                features = bundle.get("features", self._space_def.features)
                vec = []
                for f in features:
                    val = record.get(f, 0.0)
                    try:
                        vec.append(float(val) if val is not None else 0.0)
                    except (ValueError, TypeError):
                        vec.append(0.0)
                X = np.array([vec], dtype=np.float32)
                if scaler is not None:
                    X = scaler.transform(X)

            # Stage 1: Optional Anomaly Check
            anomaly_flag = False
            anomaly_score = 0.0
            if self._anomaly_detector is not None:
                try:
                    ano_model = (
                        self._anomaly_detector["model"]
                        if isinstance(self._anomaly_detector, dict)
                        else getattr(self._anomaly_detector, "model", self._anomaly_detector)
                    )
                    raw_score = float(ano_model.score_samples(X)[0])
                    anomaly_score = round(float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0)), 4)
                    anomaly_flag = bool(anomaly_score >= 0.65)
                except Exception:
                    pass

            # Stage 2: Supervised Classification
            probs_dict: Dict[str, float] = {}
            if hasattr(clf, "predict_proba"):
                probs = clf.predict_proba(X)[0]
                pred_idx = int(np.argmax(probs))
                confidence = float(probs[pred_idx])
                probs_dict = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
            else:
                pred_idx = int(clf.predict(X)[0])
                confidence = 1.0
                predicted_label = str(le.inverse_transform([pred_idx])[0])
                probs_dict = {predicted_label: 1.0}

            predicted_family = str(le.inverse_transform([pred_idx])[0])

            # HONESTY RULE:
            # If confidence is below threshold or out-of-distribution anomaly with contradictory class
            final_family = predicted_family
            flagged_unknown = False

            if confidence < self.confidence_threshold:
                final_family = AttackFamily.UNKNOWN_SUSPICIOUS.value
                flagged_unknown = True
            elif anomaly_flag and predicted_family == AttackFamily.BENIGN.value and confidence < 0.85:
                # Flow is statistically anomalous, but classifier predicted benign with non-extreme confidence
                final_family = AttackFamily.UNKNOWN_SUSPICIOUS.value
                flagged_unknown = True

            is_attack = final_family != AttackFamily.BENIGN.value

            return {
                "status": "ok",
                "family": final_family,
                "confidence": round(confidence, 4),
                "is_attack": is_attack,
                "anomaly_flag": anomaly_flag,
                "anomaly_score": anomaly_score,
                "flagged_unknown": flagged_unknown,
                "class_probabilities": probs_dict,
                "active_model": self._active_model_name or "classifier",
                "feature_space": self.feature_space,
            }

        except Exception as e:
            logger.error("Inference execution error: %s", e)
            return {"status": "error", "message": str(e)}
