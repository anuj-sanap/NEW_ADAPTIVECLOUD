"""
ml/anomaly/detector.py
Unsupervised Anomaly Detector for AdaptiveCloud Feature Spaces.
Trained exclusively on benign / normal samples of a designated feature space.
Supports IsolationForest and One-Class SVM.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM

from ml.features.extractors import FeatureExtractor

logger = logging.getLogger("ml.anomaly.detector")


class AnomalyDetector:
    """
    Unsupervised Outlier & Novelty Detector trained on pure benign telemetry.
    Computes calibrated anomaly scores and anomaly flags.
    """

    def __init__(
        self,
        feature_space: str,
        model_type: str = "isolation_forest",
        contamination: float = 0.01,
        random_state: int = 42,
        threshold: Optional[float] = None,
    ) -> None:
        self.feature_space = feature_space
        self.model_type = model_type.lower()
        self.contamination = contamination
        self.random_state = random_state
        self.threshold = threshold  # Calibrated decision threshold

        if self.model_type == "isolation_forest":
            self.model: Union[IsolationForest, OneClassSVM] = IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=self.random_state,
                n_jobs=-1,
            )
        elif self.model_type in ("one_class_svm", "ocsvm"):
            self.model = OneClassSVM(
                kernel="rbf",
                gamma="scale",
                nu=self.contamination,
            )
        else:
            raise ValueError(f"Unsupported anomaly model_type: {model_type}")

        self.is_fitted: bool = False
        self.extractor: Optional[FeatureExtractor] = None

    def fit(self, X: np.ndarray, extractor: Optional[FeatureExtractor] = None) -> AnomalyDetector:
        """
        Fits the anomaly detector on benign feature matrix X.
        Calibrates the score threshold such that contamination% of training samples are flagged.
        """
        if len(X) == 0:
            raise ValueError("Cannot fit AnomalyDetector on empty data matrix.")

        self.model.fit(X)
        self.extractor = extractor
        self.is_fitted = True

        # Calibrate threshold on benign training data
        raw_scores = self.score_samples(X)
        # Decision function: lower values mean more anomalous
        # Calibrate threshold at the (contamination * 100) percentile
        if self.threshold is None:
            self.threshold = float(np.percentile(raw_scores, self.contamination * 100))

        logger.info(
            "Fitted %s on %d samples in %s. Calibrated anomaly threshold: %.4f",
            self.model_type,
            len(X),
            self.feature_space,
            self.threshold,
        )
        return self

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Computes anomaly score for samples.
        Note: scikit-learn decision_function returns negative values for outliers,
        positive for inliers. We return raw decision_function scores.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector is not fitted.")
        return self.model.decision_function(X)

    def is_anomaly(self, X: np.ndarray) -> np.ndarray:
        """
        Returns boolean array: True if anomalous / outlier, False if benign inlier.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector is not fitted.")
        scores = self.score_samples(X)
        thresh = self.threshold if self.threshold is not None else 0.0
        return scores < thresh

    def predict_single(self, record: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Inference on a single telemetry record using attached extractor.
        Returns (is_anomaly, anomaly_score).
        """
        if not self.is_fitted or self.extractor is None:
            raise RuntimeError("Detector must be fitted with an extractor for record inference.")

        vec = self.extractor.transform_dict(record)
        score = float(self.score_samples(vec)[0])
        thresh = self.threshold if self.threshold is not None else 0.0
        flag = score < thresh
        return bool(flag), score

    def save(self, path: Path) -> Path:
        """Serializes detector to joblib."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> AnomalyDetector:
        """Loads serialized detector from joblib."""
        if not path.exists():
            raise FileNotFoundError(f"Anomaly detector not found at {path}")
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not AnomalyDetector: {type(obj)}")
        return obj
