"""
ml/training/trainer.py
Multi-Model Training Orchestrator supporting arbitrary Feature Spaces (FS-CIC, FS-UNSW, FS-KDD, FS-LIVE).
Trains XGBoost, LightGBM, and Random Forest, evaluating macro F1, weighted F1, and latency.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from ml.features.extractors import FeatureExtractor
from ml.features.spaces import get_feature_space

logger = logging.getLogger("ml.training.trainer")


class ModelTrainer:
    """
    Trains and packages threat classification models for a designated feature space.
    """

    def __init__(
        self,
        feature_space: str,
        output_dir: Optional[Path] = None,
        random_state: int = 42,
    ) -> None:
        self.feature_space = feature_space
        self.space_def = get_feature_space(feature_space)
        self.output_dir = output_dir or (Path(__file__).resolve().parent.parent / "models")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.random_state = random_state

    def train_model(
        self,
        model_name: str,
        df_train: pd.DataFrame,
        df_val: pd.DataFrame,
        label_col: str = "family",
        scaler_type: str = "robust",
    ) -> Dict[str, Any]:
        """
        Fits FeatureExtractor, fits specified model (rf, xgb, lgbm), and saves artifact bundle.
        """
        features = self.space_def.features
        target_col = label_col if label_col in df_train.columns else "label"

        # Initialize and fit FeatureExtractor
        extractor = FeatureExtractor(feature_names=features, scaler_type=scaler_type)
        X_train = extractor.fit_transform(df_train)
        X_val = extractor.transform(df_val)

        # Encode labels
        le = LabelEncoder()
        y_train_raw = df_train[target_col].astype(str).values
        y_val_raw = df_val[target_col].astype(str).values

        y_train = le.fit_transform(y_train_raw)
        # Handle unseen val classes gracefully
        classes_set = set(le.classes_)
        y_val_filtered_idx = [i for i, v in enumerate(y_val_raw) if v in classes_set]
        X_val = X_val[y_val_filtered_idx]
        y_val = le.transform(y_val_raw[y_val_filtered_idx])

        # Instantiate model
        m_lower = model_name.lower()
        if m_lower in ("random_forest", "rf"):
            clf = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1,
            )
        elif m_lower in ("xgboost", "xgb"):
            clf = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                eval_metric="mlogloss",
                random_state=self.random_state,
                n_jobs=-1,
            )
        elif m_lower in ("lightgbm", "lgbm"):
            clf = LGBMClassifier(
                n_estimators=100,
                max_depth=8,
                learning_rate=0.1,
                random_state=self.random_state,
                n_jobs=-1,
                verbose=-1,
            )
        else:
            raise ValueError(f"Unknown model name: {model_name}")

        t0 = time.perf_counter()
        clf.fit(X_train, y_train)
        train_time = round(time.perf_counter() - t0, 3)

        # Evaluation on validation set
        val_preds = clf.predict(X_val)
        val_macro_f1 = float(f1_score(y_val, val_preds, average="macro", zero_division=0))
        val_weighted_f1 = float(f1_score(y_val, val_preds, average="weighted", zero_division=0))
        val_precision = float(precision_score(y_val, val_preds, average="macro", zero_division=0))
        val_recall = float(recall_score(y_val, val_preds, average="macro", zero_division=0))

        # Latency benchmark
        t_start = time.perf_counter()
        _ = clf.predict(X_val)
        latency_ms = round(((time.perf_counter() - t_start) / max(1, len(X_val))) * 1000.0, 4)

        # Save bundle
        artifact_name = f"{m_lower}_{self.feature_space.lower()}"
        bundle_path = self.output_dir / f"{artifact_name}.joblib"
        bundle = {
            "model": clf,
            "extractor": extractor,
            "label_encoder": le,
            "feature_space": self.feature_space,
            "features": features,
            "classes": list(le.classes_),
            "name": m_lower,
            "version": "1.0.0",
        }
        joblib.dump(bundle, bundle_path)

        meta = {
            "model_name": m_lower,
            "feature_space": self.feature_space,
            "feature_count": len(features),
            "classes": list(le.classes_),
            "num_classes": len(le.classes_),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "macro_f1": round(val_macro_f1, 4),
            "weighted_f1": round(val_weighted_f1, 4),
            "precision": round(val_precision, 4),
            "recall": round(val_recall, 4),
            "inference_latency_ms": latency_ms,
            "training_time_sec": train_time,
            "created_at": datetime.now(UTC).isoformat(),
            "artifact_path": str(bundle_path),
        }

        meta_path = self.output_dir / f"{artifact_name}_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        logger.info(
            "Trained %s on %s: macro_f1=%.4f, weighted_f1=%.4f, latency=%.3fms",
            m_lower,
            self.feature_space,
            val_macro_f1,
            val_weighted_f1,
            latency_ms,
        )
        return meta
