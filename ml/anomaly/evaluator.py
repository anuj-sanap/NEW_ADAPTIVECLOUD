"""
ml/anomaly/evaluator.py
Evaluation metrics for unsupervised anomaly detectors against labeled ground truth.
"""
from __future__ import annotations

from typing import Any, Dict
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ml.anomaly.detector import AnomalyDetector


class AnomalyEvaluator:
    """
    Evaluates AnomalyDetector performance against labeled validation/test sets.
    y_true: 0 = benign, 1 = attack/anomaly.
    """

    @staticmethod
    def evaluate(
        detector: AnomalyDetector,
        X: np.ndarray,
        y_true: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Computes precision, recall, f1, and roc_auc for the anomaly detector.
        """
        y_pred_bool = detector.is_anomaly(X)
        y_pred = y_pred_bool.astype(int)

        # Raw scores: decision_function (higher = inlier, lower = outlier)
        # For ROC-AUC, outlier score should be higher for attacks: -decision_function
        raw_scores = detector.score_samples(X)
        outlier_scores = -raw_scores

        try:
            roc_auc = float(roc_auc_score(y_true, outlier_scores))
        except Exception:
            roc_auc = 0.0

        try:
            pr_auc = float(average_precision_score(y_true, outlier_scores))
        except Exception:
            pr_auc = 0.0

        p = float(precision_score(y_true, y_pred, zero_division=0))
        r = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        return {
            "model_type": detector.model_type,
            "feature_space": detector.feature_space,
            "threshold": detector.threshold,
            "samples": int(len(y_true)),
            "anomalies_detected": int(np.sum(y_pred)),
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
        }
