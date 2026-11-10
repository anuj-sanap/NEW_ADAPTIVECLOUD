"""
ml/training/train_anomaly.py
Unsupervised anomaly detection training using Isolation Forest.
Trained strictly on benign network flow patterns to detect zero-day or outlier attacks.
Saves model artifact via joblib and structured metadata JSON.
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
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_anomaly")


def train_isolation_forest(
    benign_train_path: Path,
    val_path: Path,
    output_dir: Path,
    n_estimators: int = 100,
    contamination: float = 0.01,
    random_state: int = 42,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df_benign = pd.read_parquet(benign_train_path)
    df_val = pd.read_parquet(val_path)

    validate_features(df_benign[list(CANONICAL_FEATURES)])
    validate_features(df_val[list(CANONICAL_FEATURES)])

    X_train = df_benign[list(CANONICAL_FEATURES)].values
    X_val = df_val[list(CANONICAL_FEATURES)].values

    logger.info("Fitting StandardScaler on %d benign training flows ...", len(X_train))
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    logger.info("Training IsolationForest (n_estimators=%d, contamination=%.3f) ...", n_estimators, contamination)
    t0 = time.perf_counter()
    iso = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    iso.fit(X_train_scaled)
    train_time_sec = round(time.perf_counter() - t0, 3)

    # Measure inference latency on validation set
    X_val_scaled = scaler.transform(X_val)
    t_inf_start = time.perf_counter()
    _ = iso.score_samples(X_val_scaled)
    inf_latency_ms = round(((time.perf_counter() - t_inf_start) / max(1, len(X_val))) * 1000.0, 4)

    # Save artifact containing both scaler and isolation forest
    artifact_path = output_dir / "isolation_forest.joblib"
    artifact_bundle = {
        "model": iso,
        "scaler": scaler,
        "features": list(CANONICAL_FEATURES),
        "task": "anomaly",
        "name": "isolation_forest",
        "version": "1.0.0",
    }
    joblib.dump(artifact_bundle, artifact_path)

    # Save metadata JSON
    meta_path = output_dir / "isolation_forest_meta.json"
    metadata = {
        "name": "isolation_forest",
        "task": "anomaly",
        "version": "1.0.0",
        "features": list(CANONICAL_FEATURES),
        "feature_count": len(CANONICAL_FEATURES),
        "scaler": "StandardScaler",
        "training_time_sec": train_time_sec,
        "inference_latency_ms": inf_latency_ms,
        "train_samples": len(X_train),
        "contamination": contamination,
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_path": str(artifact_path.relative_to(REPO_ROOT)),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info("Isolation Forest artifact saved: %s (train_time=%.2fs, latency=%.3fms)", artifact_path.name, train_time_sec, inf_latency_ms)
    return artifact_path, meta_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train unsupervised Isolation Forest on benign flows")
    parser.add_argument("--train-path", type=str, default="ml/data/cache/benign_train.parquet")
    parser.add_argument("--val-path", type=str, default="ml/data/cache/val.parquet")
    parser.add_argument("--output-dir", type=str, default="ml/models")
    args = parser.parse_args()

    train_isolation_forest(
        benign_train_path=REPO_ROOT / args.train_path,
        val_path=REPO_ROOT / args.val_path,
        output_dir=REPO_ROOT / args.output_dir,
    )


if __name__ == "__main__":
    main()
