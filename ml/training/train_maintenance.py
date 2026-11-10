"""
ml/training/train_maintenance.py
Trains predictive maintenance models for Windows infrastructure:
1. CPU Overload threshold breach (>85% utilization) within 15-minute horizon.
2. Memory Exhaustion threshold breach (>90% utilization) within 30-minute horizon.
3. Disk Fill progression estimator using Theil-Sen robust linear regression.

Features extracted: rolling mean, std, EWMA, linear slope, and rate of change.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import TheilSenRegressor
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_maintenance")

FEATURE_NAMES = [
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_std_6",
    "ewma_03",
    "rate_of_change",
    "slope_per_min",
    "current_val",
]


def generate_synthetic_metric_series(n_samples: int = 1440) -> pd.DataFrame:
    """
    Generates realistic 1-minute interval system metrics:
    - Diurnal base load with random workload bursts
    - Gradual memory leaks simulating unmanaged Windows services
    - Linear disk usage growth simulating log accumulations
    """
    np.random.seed(42)
    t = np.arange(n_samples)

    # CPU: base diurnal + spikes
    diurnal_cpu = 25.0 + 15.0 * np.sin(2 * np.pi * t / 1440)
    cpu_noise = np.random.normal(0, 5, n_samples)
    cpu = diurnal_cpu + cpu_noise
    # Inject 8 overload bursts
    for _ in range(8):
        start = np.random.randint(50, n_samples - 60)
        burst_len = np.random.randint(15, 45)
        cpu[start : start + burst_len] += np.random.uniform(40, 55)
    cpu = np.clip(cpu, 2.0, 100.0)

    # Memory: gradual upward drift (leak) with occasional cleanup
    mem_base = 45.0 + 5.0 * np.sin(2 * np.pi * t / 1440)
    mem_leak = (t % 360) * 0.12
    mem_noise = np.random.normal(0, 2, n_samples)
    mem = np.clip(mem_base + mem_leak + mem_noise, 15.0, 99.0)

    # Disk: steady accumulation
    disk_base = 65.0
    disk_growth = (t / 1440.0) * 1.5  # 1.5% per day
    disk = np.clip(disk_base + disk_growth + np.random.normal(0, 0.1, n_samples), 10.0, 100.0)

    df = pd.DataFrame({
        "minute": t,
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
    })
    return df


def extract_features(series: pd.Series) -> pd.DataFrame:
    """Extract rolling and trend features from a 1D time series."""
    df = pd.DataFrame({"current_val": series})
    df["rolling_mean_3"] = series.rolling(3, min_periods=1).mean()
    df["rolling_mean_6"] = series.rolling(6, min_periods=1).mean()
    df["rolling_std_6"] = series.rolling(6, min_periods=1).std().fillna(0.0)

    # EWMA alpha=0.3
    df["ewma_03"] = series.ewm(alpha=0.3, adjust=False).mean()

    # Rate of change (5-minute delta)
    df["rate_of_change"] = (series - series.shift(5)).fillna(0.0)

    # Slope over past 5 intervals
    def _slope(window: np.ndarray) -> float:
        if len(window) < 2:
            return 0.0
        x = np.arange(len(window))
        return float(np.polyfit(x, window, 1)[0])

    df["slope_per_min"] = series.rolling(5, min_periods=2).apply(_slope, raw=True).fillna(0.0)
    return df[FEATURE_NAMES]


def train_threshold_model(
    df: pd.DataFrame,
    metric_col: str,
    threshold: float,
    horizon_min: int,
    output_path: Path,
) -> dict[str, Any]:
    """Trains a calibrated Gradient Boosting classifier for future threshold breach."""
    X = extract_features(df[metric_col])

    # Target: Will max value in next `horizon_min` exceed threshold?
    future_max = df[metric_col].iloc[::-1].rolling(horizon_min, min_periods=1).max().iloc[::-1].shift(-horizon_min)
    y = (future_max >= threshold).astype(int).fillna(0)

    # Time-based split (75% train, 25% test)
    split_idx = int(len(X) * 0.75)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    base_clf = GradientBoostingClassifier(
        n_estimators=60,
        max_depth=3,
        learning_rate=0.08,
        random_state=42,
    )
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)

    t0 = time.perf_counter()
    calibrated_clf.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    preds = calibrated_clf.predict(X_test)
    probs = calibrated_clf.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, preds))
    prec = float(precision_score(y_test, preds, zero_division=0))
    rec = float(recall_score(y_test, preds, zero_division=0))
    f1 = float(f1_score(y_test, preds, zero_division=0))
    try:
        auc = float(roc_auc_score(y_test, probs))
    except Exception:
        auc = 0.5
    brier = float(brier_score_loss(y_test, probs))

    joblib.dump(calibrated_clf, output_path)

    metadata = {
        "metric": metric_col,
        "threshold": threshold,
        "horizon_min": horizon_min,
        "features": FEATURE_NAMES,
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "train_time_sec": round(train_time, 4),
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
        },
        "created_at": datetime.now(UTC).isoformat(),
    }

    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "Trained %s threshold model (horizon=%dm): Acc=%.4f F1=%.4f AUC=%.4f Brier=%.4f",
        metric_col, horizon_min, acc, f1, auc, brier,
    )
    return metadata


def train_disk_regression_model(
    df: pd.DataFrame,
    output_path: Path,
) -> dict[str, Any]:
    """Trains a Theil-Sen robust estimator for disk growth rate projection."""
    t = df["minute"].values.reshape(-1, 1)
    y = df["disk"].values

    split_idx = int(len(t) * 0.75)
    t_train, t_test = t[:split_idx], t[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = TheilSenRegressor(random_state=42)
    model.fit(t_train, y_train)

    score = float(model.score(t_test, y_test))
    slope_per_min = float(model.coef_[0])

    joblib.dump(model, output_path)

    metadata = {
        "model_type": "TheilSenRegressor",
        "metric": "disk",
        "slope_per_minute": round(slope_per_min, 6),
        "slope_per_day": round(slope_per_min * 1440.0, 4),
        "r2_test_score": round(score, 4),
        "created_at": datetime.now(UTC).isoformat(),
    }
    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Trained Theil-Sen disk regression: Slope=%.6f/min R2=%.4f", slope_per_min, score)
    return metadata


def run_training(output_dir: Path, samples: int = 2880) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating %d metric telemetry samples for maintenance modeling...", samples)
    df = generate_synthetic_metric_series(n_samples=samples)

    cpu_path = output_dir / "maintenance_cpu_15m.joblib"
    cpu_meta = train_threshold_model(df, "cpu", threshold=85.0, horizon_min=15, output_path=cpu_path)

    mem_path = output_dir / "maintenance_mem_30m.joblib"
    mem_meta = train_threshold_model(df, "mem", threshold=90.0, horizon_min=30, output_path=mem_path)

    disk_path = output_dir / "maintenance_disk_theilsen.joblib"
    disk_meta = train_disk_regression_model(df, output_path=disk_path)

    summary = {
        "cpu_15m": cpu_meta,
        "mem_30m": mem_meta,
        "disk_theilsen": disk_meta,
    }

    summary_file = output_dir / "maintenance_models_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Maintenance model artifacts successfully saved to %s", output_dir)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train predictive maintenance models")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "ml" / "models")
    parser.add_argument("--samples", type=int, default=2880, help="Number of 1-minute metric intervals (default: 48h = 2880)")
    args = parser.parse_args()

    run_training(args.output_dir, args.samples)


if __name__ == "__main__":
    main()
