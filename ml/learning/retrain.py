"""
ml/learning/retrain.py
Controlled, auditable retraining pipeline with catastrophic forgetting mitigation (replay buffer)
and a strict Champion/Challenger promotion gate.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
from xgboost import XGBClassifier

from ml.features.feature_map import CANONICAL_FEATURES

logger = logging.getLogger("ml.learning.retrain")


def evaluate_promotion_gate(
    champion_metrics: dict[str, Any],
    challenger_metrics: dict[str, Any],
    min_f1_margin: float = 0.005,
    recall_tolerance: float = 0.05,
) -> tuple[bool, list[str]]:
    """
    Evaluates whether a Challenger model qualifies to replace the Champion model.
    Criteria:
    1. Overall Macro-F1 improves by at least `min_f1_margin`.
    2. Per-class recall does not degrade by more than `recall_tolerance` on any attack class.
    3. Benign class recall (false alarm control) does not drop by more than 0.02.
    """
    reasons: list[str] = []
    can_promote = True

    champ_f1 = float(champion_metrics.get("macro_f1", 0.0))
    chall_f1 = float(challenger_metrics.get("macro_f1", 0.0))

    # 1. Macro-F1 margin test
    f1_delta = chall_f1 - champ_f1
    if f1_delta < min_f1_margin:
        can_promote = False
        reasons.append(
            f"Macro-F1 did not achieve required margin (+{min_f1_margin:.4f}). "
            f"Champion: {champ_f1:.4f}, Challenger: {chall_f1:.4f} (Delta: {f1_delta:+.4f})"
        )
    else:
        reasons.append(f"Macro-F1 improved by {f1_delta:+.4f} (>= +{min_f1_margin:.4f})")

    # 2. Per-class recall tolerance test
    champ_recalls = champion_metrics.get("per_class_recall", {})
    chall_recalls = challenger_metrics.get("per_class_recall", {})

    for cls_name, c_rec in champ_recalls.items():
        chall_rec = chall_recalls.get(cls_name, 0.0)
        rec_delta = chall_rec - c_rec
        if rec_delta < -recall_tolerance:
            can_promote = False
            reasons.append(
                f"Class '{cls_name}' recall degraded beyond tolerance (-{recall_tolerance:.2f}). "
                f"Champion: {c_rec:.4f}, Challenger: {chall_rec:.4f} (Delta: {rec_delta:+.4f})"
            )

    # 3. Benign recall preservation (False Positive guard)
    champ_benign = champ_recalls.get("benign", 1.0)
    chall_benign = chall_recalls.get("benign", 1.0)
    if chall_benign < champ_benign - 0.02:
        can_promote = False
        reasons.append(
            f"Benign recall degraded by {(chall_benign - champ_benign):.4f} (> 0.02 false alarm budget)."
        )

    return can_promote, reasons


class ControlledRetrainer:
    """Manages experience replay buffering and training of candidate models."""

    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def create_replay_dataset(
        self,
        baseline_df: pd.DataFrame,
        feedback_df: pd.DataFrame,
        replay_ratio: float = 0.70,
    ) -> pd.DataFrame:
        """
        Combines baseline training distributions with human analyst feedback labels
        using experience replay to prevent catastrophic forgetting.
        """
        if feedback_df.empty:
            return baseline_df.copy()

        n_feedback = len(feedback_df)
        n_replay = int(round(n_feedback * (replay_ratio / (1.0 - replay_ratio))))
        n_replay = max(n_replay, min(len(baseline_df), 100))

        # Stratified or uniform sampling from baseline
        replay_sample = baseline_df.sample(n=min(n_replay, len(baseline_df)), random_state=42)

        combined = pd.concat([replay_sample, feedback_df], ignore_index=True)
        return combined.sample(frac=1.0, random_state=42).reset_index(drop=True)

    def train_candidate(
        self,
        train_df: pd.DataFrame,
        holdout_df: pd.DataFrame,
        target_col: str = "label",
        version: str = "v2.0-candidate",
    ) -> dict[str, Any]:
        """Trains a candidate XGBoost/RandomForest model and calculates evaluation metrics."""
        feature_cols = [c for c in CANONICAL_FEATURES if c in train_df.columns]

        X_train = train_df[feature_cols].fillna(0.0)
        y_train = train_df[target_col].astype(str)

        X_holdout = holdout_df[feature_cols].fillna(0.0)
        y_holdout = holdout_df[target_col].astype(str)

        classes = sorted(list(set(y_train.unique()) | set(y_holdout.unique())))
        label_to_idx = {c: i for i, c in enumerate(classes)}

        y_train_idx = y_train.map(label_to_idx)

        # Train candidate model
        clf = XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            eval_metric="mlogloss",
            random_state=42,
        )
        clf.fit(X_train, y_train_idx)

        preds_idx = clf.predict(X_holdout)
        preds = [classes[i] for i in preds_idx]

        macro_f1 = float(f1_score(y_holdout, preds, average="macro", zero_division=0))
        prec = float(precision_score(y_holdout, preds, average="macro", zero_division=0))
        rec = float(recall_score(y_holdout, preds, average="macro", zero_division=0))

        report = classification_report(y_holdout, preds, output_dict=True, zero_division=0)
        per_class_recall = {}
        for c in classes:
            if c in report:
                per_class_recall[c] = round(report[c]["recall"], 4)

        artifact_name = f"classifier_candidate_{version}.joblib"
        artifact_path = self.models_dir / artifact_name

        payload = {
            "model": clf,
            "classes": classes,
            "features": feature_cols,
            "version": version,
            "created_at": datetime.now(UTC).isoformat(),
        }
        joblib.dump(payload, artifact_path)

        metrics = {
            "macro_f1": round(macro_f1, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "per_class_recall": per_class_recall,
            "dataset_size": len(train_df),
            "holdout_size": len(holdout_df),
        }

        # Write metadata JSON
        meta_path = artifact_path.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": version,
                "artifact": str(artifact_path),
                "metrics": metrics,
            }, f, indent=2)

        return {
            "version": version,
            "artifact_path": str(artifact_path),
            "metrics": metrics,
        }
