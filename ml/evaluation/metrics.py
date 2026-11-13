"""
ml/evaluation/metrics.py
Strict, ground-truth based metrics computation.
HONESTY RULE: Every metric must derive strictly from evaluated ground-truth test/val sets.
Zero synthetic, hardcoded, or fabricated numbers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)


def compute_classification_metrics(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    class_names: Optional[List[str]] = None,
    latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes rigorous classification metrics across all classes.
    """
    y_t = np.array(y_true)
    y_p = np.array(y_pred)

    if len(y_t) == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")

    acc = float(accuracy_score(y_t, y_p))
    macro_f1 = float(f1_score(y_t, y_p, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_t, y_p, average="weighted", zero_division=0))
    macro_p = float(precision_score(y_t, y_p, average="macro", zero_division=0))
    macro_r = float(recall_score(y_t, y_p, average="macro", zero_division=0))

    report = classification_report(
        y_t,
        y_p,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    per_class: Dict[str, Dict[str, float]] = {}
    if class_names:
        for c in class_names:
            if c in report:
                per_class[c] = {
                    "precision": round(float(report[c]["precision"]), 4),
                    "recall": round(float(report[c]["recall"]), 4),
                    "f1": round(float(report[c]["f1-score"]), 4),
                    "support": int(report[c]["support"]),
                }

    res: Dict[str, Any] = {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "precision": round(macro_p, 4),
        "recall": round(macro_r, 4),
        "sample_count": int(len(y_t)),
        "per_class": per_class,
    }
    if latency_ms is not None:
        res["inference_latency_ms"] = round(latency_ms, 4)

    return res
