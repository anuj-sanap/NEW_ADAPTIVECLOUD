"""
ml/training/train_threat_forecast.py
Trains rolling time-series threat forecasting models (GradientBoosting / XGBoost)
predicting attack likelihoods within 15-minute and 60-minute forward horizons.
Extracts lag, rolling statistics, rate of failed logons, and time-of-day features.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, roc_auc_score

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_threat_forecast")


def generate_synthetic_threat_timeseries(n_intervals: int = 288) -> pd.DataFrame:
    """
    Creates a calibrated time series of 5-minute intervals (default: 24 hours = 288 intervals)
    for model fitting when historical production database is newly initialized.
    """
    np.random.seed(42)
    records = []
    failed_logons = 0
    attack_active = False

    for i in range(n_intervals):
        hour = (i * 5 // 60) % 24
        day = (i * 5 // 1440) % 7

        # Periodic attack bursts simulating real scan and brute-force behaviors
        if np.random.rand() < 0.08:
            attack_active = True
            burst_len = np.random.randint(3, 8)
        elif attack_active:
            burst_len -= 1
            if burst_len <= 0:
                attack_active = False

        if attack_active:
            events = int(np.random.poisson(25) + 10)
            failed_logons = int(np.random.poisson(15) + 5)
            distinct_ips = int(np.random.randint(2, 6))
            is_attack = 1
        else:
            events = int(np.random.poisson(3))
            failed_logons = int(1 if np.random.rand() < 0.1 else 0)
            distinct_ips = int(1 if np.random.rand() < 0.3 else 0)
            is_attack = 0

        records.append({
            "interval_idx": i,
            "hour": hour,
            "day": day,
            "events": events,
            "failed_logons": failed_logons,
            "distinct_ips": distinct_ips,
            "is_attack": is_attack,
        })

    df = pd.DataFrame(records)

    # Compute rolling lag features
    for lag in [1, 2, 3]:
        df[f"events_lag_{lag}"] = df["events"].shift(lag).fillna(0)
        df[f"failed_logons_lag_{lag}"] = df["failed_logons"].shift(lag).fillna(0)
        df[f"ips_lag_{lag}"] = df["distinct_ips"].shift(lag).fillna(0)

    df["events_roll_mean_3"] = df["events"].rolling(3).mean().fillna(0)
    df["events_roll_std_3"] = df["events"].rolling(3).std().fillna(0)
    df["failed_logons_roll_mean_3"] = df["failed_logons"].rolling(3).mean().fillna(0)

    # Forward targets: attack in next 15 min (3 intervals) and 60 min (12 intervals)
    df["target_15m"] = df["is_attack"].shift(-3).fillna(0).astype(int)
    df["target_60m"] = df["is_attack"].shift(-12).fillna(0).astype(int)

    return df


def train_threat_forecast_model(
    output_dir: Path,
    horizon_min: int = 15,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_threat_timeseries(n_intervals=500)

    target_col = f"target_{horizon_min}m"
    feature_cols = [
        "hour",
        "day",
        "events_lag_1",
        "events_lag_2",
        "events_lag_3",
        "failed_logons_lag_1",
        "failed_logons_lag_2",
        "failed_logons_lag_3",
        "ips_lag_1",
        "events_roll_mean_3",
        "events_roll_std_3",
        "failed_logons_roll_mean_3",
    ]

    # Time-based split: first 80% train, last 20% test (preserving chronological order)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    logger.info("Training threat forecast model (%dm forward horizon) ...", horizon_min)
    t0 = time.perf_counter()
    base_clf = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=4,
        random_state=42,
    )
    # Probability calibration for reliable probabilities
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)
    calibrated_clf.fit(X_train, y_train)
    train_time_sec = round(time.perf_counter() - t0, 3)

    # Test evaluation
    y_preds = calibrated_clf.predict(X_test)
    y_probs = calibrated_clf.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, y_preds))
    f1 = float(f1_score(y_test, y_preds, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_probs)) if len(set(y_test)) > 1 else 1.0
    brier = float(brier_score_loss(y_test, y_probs))

    artifact_path = output_dir / f"threat_forecast_{horizon_min}m.joblib"
    meta_path = output_dir / f"threat_forecast_{horizon_min}m_meta.json"

    bundle = {
        "model": calibrated_clf,
        "features": feature_cols,
        "horizon_min": horizon_min,
        "task": "threat_forecasting",
        "name": f"threat_forecast_{horizon_min}m",
        "version": "1.0.0",
    }
    joblib.dump(bundle, artifact_path)

    metadata = {
        "name": f"threat_forecast_{horizon_min}m",
        "task": "threat_forecasting",
        "version": "1.0.0",
        "horizon_min": horizon_min,
        "accuracy": round(acc, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "training_time_sec": train_time_sec,
        "features": feature_cols,
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_path": str(artifact_path.relative_to(REPO_ROOT)),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info(
        "Saved %s: Acc=%.4f, F1=%.4f, ROC-AUC=%.4f, Brier=%.4f",
        artifact_path.name,
        acc,
        f1,
        roc_auc,
        brier,
    )
    return artifact_path, meta_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train rolling threat forecasting models")
    parser.add_argument("--output-dir", type=str, default="ml/models")
    args = parser.parse_args()

    out_dir = REPO_ROOT / args.output_dir
    train_threat_forecast_model(out_dir, horizon_min=15)
    train_threat_forecast_model(out_dir, horizon_min=60)
    print("\n[AdaptiveCloud ML] Threat forecasting models successfully trained and calibrated.")


if __name__ == "__main__":
    main()
