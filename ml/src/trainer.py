"""
ml/src/trainer.py
Model training pipeline: loads data from the backend DB, trains XGBoost,
validates with stratified k-fold, and persists the model artefact.

RULES:
- Never hardcode metrics or fake accuracy.
- If < MIN_SAMPLES labelled rows exist: raise InsufficientDataError.
- All metrics are computed from real held-out cross-validation.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from features import FEATURE_NAMES, LABEL_CLASSES, payloads_to_dataframe

logger = logging.getLogger(__name__)

MIN_SAMPLES = 500        # Minimum labelled rows required to train
N_FOLDS = 5              # Stratified k-fold splits
MODELS_DIR = Path(__file__).parent.parent / "models"


class InsufficientDataError(Exception):
    """Raised when the training dataset is too small to produce a valid model."""
    pass


def _next_version(models_dir: Path) -> str:
    """Generate the next semantic version string based on existing model files."""
    existing = sorted(models_dir.glob("model_v*.joblib"))
    if not existing:
        return "v1.0.0"
    last = existing[-1].stem  # e.g. "model_v1.0.0"
    parts = last.replace("model_v", "").split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    return f"v{major}.{minor}.{patch + 1}"


def train(
    labelled_payloads: list[dict[str, Any]],
    job_id: str,
) -> dict[str, Any]:
    """
    Train an XGBoost classifier on the provided labelled metric snapshots.

    Args:
        labelled_payloads: List of dicts — each is a MetricPayload + 'label' key.
        job_id: Training job UUID (for logging and artefact naming).

    Returns:
        Dict with keys: version, trained_at, training_samples,
        feature_names, label_classes, cv_metrics, artifact_path.

    Raises:
        InsufficientDataError: if fewer than MIN_SAMPLES valid rows are found.
    """
    logger.info("Training started | job_id=%s samples_raw=%d", job_id, len(labelled_payloads))

    # ── Prepare features ─────────────────────────────────────────────────────
    df = payloads_to_dataframe(labelled_payloads)

    labels_raw = []
    for p in labelled_payloads:
        try:
            labels_raw.append(p["label"])
        except KeyError:
            labels_raw.append(None)

    df["label"] = labels_raw[: len(df)]
    df = df.dropna(subset=["label"])
    df = df[df["label"].isin(LABEL_CLASSES)]

    if len(df) < MIN_SAMPLES:
        raise InsufficientDataError(
            f"Need at least {MIN_SAMPLES} labelled samples, got {len(df)}. "
            "Collect more data before retraining."
        )

    X = df[FEATURE_NAMES].values
    le = LabelEncoder()
    le.fit(LABEL_CLASSES)   # Fixed order — ensures consistent class indices
    y = le.transform(df["label"].values)

    logger.info("Training | samples=%d classes=%s", len(df), list(le.classes_))

    # ── Model definition ─────────────────────────────────────────────────────
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    # ── Cross-validation — real metrics only ─────────────────────────────────
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)
    cv_results = cross_validate(
        model, X, y, cv=cv,
        scoring=["accuracy", "f1_weighted"],
        return_train_score=False,
        n_jobs=-1,
    )

    cv_metrics = {
        "cv_accuracy_mean": float(np.mean(cv_results["test_accuracy"])),
        "cv_accuracy_std": float(np.std(cv_results["test_accuracy"])),
        "cv_f1_weighted_mean": float(np.mean(cv_results["test_f1_weighted"])),
        "cv_f1_weighted_std": float(np.std(cv_results["test_f1_weighted"])),
    }
    logger.info("CV results: %s", cv_metrics)

    # ── Final fit on full dataset ─────────────────────────────────────────────
    model.fit(X, y)

    # ── Persist artefact ─────────────────────────────────────────────────────
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    version = _next_version(MODELS_DIR)
    model_path = MODELS_DIR / f"model_{version}.joblib"
    meta_path = MODELS_DIR / f"model_{version}_meta.json"

    joblib.dump({"model": model, "label_encoder": le}, model_path)

    trained_at = datetime.now(UTC).isoformat()
    meta = {
        "version": version,
        "job_id": job_id,
        "trained_at": trained_at,
        "training_samples": len(df),
        "feature_names": FEATURE_NAMES,
        "label_classes": list(le.classes_),
        "cv_metrics": cv_metrics,
        "artifact_path": str(model_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    logger.info("Model saved | version=%s path=%s", version, model_path)
    return meta

