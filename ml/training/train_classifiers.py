"""
ml/training/train_classifiers.py
Multi-class supervised threat classification training pipeline.
Trains 4 model architectures:
1. Random Forest (balanced class weights)
2. XGBoost (gradient boosted trees)
3. Decision Tree (interpretable baseline)
4. Support Vector Machine (RBF kernel, scaled, calibrated on subsample)
Handles class imbalance, fits LabelEncoder, tracks training time and validation score.
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_classifiers")


def train_all_classifiers(
    train_path: Path,
    val_path: Path,
    output_dir: Path,
    random_state: int = 42,
) -> dict[str, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df_train = pd.read_parquet(train_path)
    df_val = pd.read_parquet(val_path)

    validate_features(df_train[list(CANONICAL_FEATURES)])
    validate_features(df_val[list(CANONICAL_FEATURES)])

    X_train = df_train[list(CANONICAL_FEATURES)].values
    y_train_raw = df_train["label"].values

    X_val = df_val[list(CANONICAL_FEATURES)].values
    y_val_raw = df_val["label"].values

    # Fit shared LabelEncoder
    le = LabelEncoder()
    y_train = le.fit_transform(y_train_raw)
    y_val = le.transform(y_val_raw)

    classes = list(le.classes_)
    logger.info("Fitted LabelEncoder on %d classes: %s", len(classes), classes)

    # Pre-fit StandardScaler for models that require scaling (SVM)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    models_config = {
        "random_forest": {
            "model": RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=-1,
            ),
            "use_scaled": False,
            "subsample": None,
        },
        "xgboost": {
            "model": XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                eval_metric="mlogloss",
                random_state=random_state,
                n_jobs=-1,
            ),
            "use_scaled": False,
            "subsample": None,
        },
        "decision_tree": {
            "model": DecisionTreeClassifier(
                max_depth=12,
                class_weight="balanced",
                random_state=random_state,
            ),
            "use_scaled": False,
            "subsample": None,
        },
        "svm": {
            "model": SVC(
                C=1.0,
                kernel="rbf",
                probability=True,
                class_weight="balanced",
                random_state=random_state,
            ),
            "use_scaled": True,
            # Subsample SVM to 3000 rows to avoid quadratic O(N^2) explosion on laptops
            "subsample": 3000,
        },
    }

    results: dict[str, dict[str, Any]] = {}

    for name, cfg in models_config.items():
        logger.info("Training %s ...", name)
        clf = cfg["model"]
        use_scaled = cfg["use_scaled"]
        subsample = cfg["subsample"]

        cur_X_train = X_train_scaled if use_scaled else X_train
        cur_y_train = y_train
        cur_X_val = X_val_scaled if use_scaled else X_val

        if subsample and len(cur_X_train) > subsample:
            idx = np.random.RandomState(random_state).choice(len(cur_X_train), size=subsample, replace=False)
            cur_X_train = cur_X_train[idx]
            cur_y_train = cur_y_train[idx]

        t0 = time.perf_counter()
        clf.fit(cur_X_train, cur_y_train)
        train_time_sec = round(time.perf_counter() - t0, 3)

        # Measure validation macro F1
        val_preds = clf.predict(cur_X_val)
        val_macro_f1 = float(f1_score(y_val, val_preds, average="macro"))

        # Measure single-sample inference latency
        t_lat_start = time.perf_counter()
        _ = clf.predict(cur_X_val)
        inf_latency_ms = round(((time.perf_counter() - t_lat_start) / max(1, len(cur_X_val))) * 1000.0, 4)

        # Save bundle
        artifact_path = output_dir / f"{name}.joblib"
        bundle = {
            "model": clf,
            "scaler": scaler if use_scaled else None,
            "label_encoder": le,
            "features": list(CANONICAL_FEATURES),
            "name": name,
            "task": "attack_classification",
            "version": "1.0.0",
            "classes": classes,
        }
        joblib.dump(bundle, artifact_path)

        # Save individual metadata JSON
        meta_path = output_dir / f"{name}_meta.json"
        meta = {
            "name": name,
            "task": "attack_classification",
            "version": "1.0.0",
            "classes": classes,
            "features": list(CANONICAL_FEATURES),
            "feature_count": len(CANONICAL_FEATURES),
            "scaler": "StandardScaler" if use_scaled else "None",
            "val_macro_f1": round(val_macro_f1, 4),
            "training_time_sec": train_time_sec,
            "inference_latency_ms": inf_latency_ms,
            "train_samples": len(cur_X_train),
            "created_at": datetime.now(UTC).isoformat(),
            "artifact_path": str(artifact_path.relative_to(REPO_ROOT)),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        results[name] = meta
        logger.info(
            "Completed %s: val_macro_f1=%.4f, train_time=%.2fs, latency=%.3fms",
            name,
            val_macro_f1,
            train_time_sec,
            inf_latency_ms,
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train multi-class intrusion classifiers")
    parser.add_argument("--train-path", type=str, default="ml/data/cache/train.parquet")
    parser.add_argument("--val-path", type=str, default="ml/data/cache/val.parquet")
    parser.add_argument("--output-dir", type=str, default="ml/models")
    args = parser.parse_args()

    train_all_classifiers(
        train_path=REPO_ROOT / args.train_path,
        val_path=REPO_ROOT / args.val_path,
        output_dir=REPO_ROOT / args.output_dir,
    )


if __name__ == "__main__":
    main()
