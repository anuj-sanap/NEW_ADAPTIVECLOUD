"""
ml/tests/test_anomaly.py
Tests for Unsupervised Anomaly Detection and Evaluator.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.anomaly.detector import AnomalyDetector
from ml.anomaly.evaluator import AnomalyEvaluator
from ml.features.extractors import FeatureExtractor
from ml.features.spaces import get_feature_space


def test_anomaly_detector_training_and_scoring(synthetic_cic_df: pd.DataFrame, tmp_path: Path) -> None:
    space = get_feature_space("FS-CIC")
    extractor = FeatureExtractor(feature_names=space.features, scaler_type="robust")

    # Train only on benign samples
    benign_df = synthetic_cic_df[synthetic_cic_df["family"] == "benign"]
    X_benign = extractor.fit_transform(benign_df)

    detector = AnomalyDetector(feature_space="FS-CIC", model_type="isolation_forest", contamination=0.05)
    detector.fit(X_benign, extractor=extractor)

    assert detector.is_fitted
    assert detector.threshold is not None

    # Test single-record inference
    record = {f: 10.0 for f in space.features}
    is_ano, score = detector.predict_single(record)
    assert isinstance(is_ano, bool)
    assert isinstance(score, float)

    # Test serialization
    save_path = tmp_path / "iso_test.joblib"
    detector.save(save_path)
    loaded = AnomalyDetector.load(save_path)
    assert loaded.is_fitted
    assert loaded.feature_space == "FS-CIC"


def test_anomaly_evaluator(synthetic_cic_df: pd.DataFrame) -> None:
    space = get_feature_space("FS-CIC")
    extractor = FeatureExtractor(feature_names=space.features)
    X = extractor.fit_transform(synthetic_cic_df)
    y_true = synthetic_cic_df["l1"].values

    # Fit detector on all samples for evaluation test
    detector = AnomalyDetector(feature_space="FS-CIC", model_type="isolation_forest", contamination=0.10)
    detector.fit(X, extractor=extractor)

    metrics = AnomalyEvaluator.evaluate(detector, X, y_true)
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert metrics["samples"] == len(synthetic_cic_df)
