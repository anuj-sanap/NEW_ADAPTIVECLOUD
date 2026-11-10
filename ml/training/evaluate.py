"""
ml/training/evaluate.py
Rigorous evaluation suite assessing classifiers on the held-out test partition.
Calculates Accuracy, Precision, Recall, Macro F1, Per-Class metrics, ROC-AUC,
Inference Latency, and renders Confusion Matrix PNGs.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any
import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate")


def plot_confusion_matrix(
    cm: np.ndarray,
    classes: list[str],
    output_path: Path,
    title: str = "Confusion Matrix",
) -> None:
    """Render and save a clear confusion matrix plot."""
    fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=classes,
        yticklabels=classes,
        title=title,
        ylabel="True Label",
        xlabel="Predicted Label",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j,
                i,
                format(cm[i, j], "d"),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
            )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def evaluate_classifier(
    bundle_path: Path,
    test_df: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    bundle = joblib.load(bundle_path)
    model = bundle["model"]
    scaler = bundle.get("scaler")
    le = bundle["label_encoder"]
    classes = list(le.classes_)
    name = bundle["name"]

    X_test = test_df[list(CANONICAL_FEATURES)].values
    y_test_raw = test_df["label"].values
    y_test = le.transform(y_test_raw)

    if scaler is not None:
        X_test = scaler.transform(X_test)

    # Measure latency
    t0 = time.perf_counter()
    y_pred = model.predict(X_test)
    inf_latency_ms = round(((time.perf_counter() - t0) / max(1, len(X_test))) * 1000.0, 4)

    # Basic metrics
    acc = float(accuracy_score(y_test, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)

    # Per-class metrics
    report_dict = classification_report(y_test, y_pred, target_names=classes, output_dict=True, zero_division=0)
    per_class = {c: report_dict[c] for c in classes if c in report_dict}

    # ROC-AUC (multi-class OVR)
    roc_auc = 0.0
    try:
        if hasattr(model, "predict_proba"):
            y_probs = model.predict_proba(X_test)
            roc_auc = float(roc_auc_score(y_test, y_probs, multi_class="ovr", average="macro"))
    except Exception as e:
        logger.warning("ROC-AUC computation skipped for %s: %s", name, e)

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    cm_path = output_dir / f"{name}_cm.png"
    plot_confusion_matrix(cm, classes, cm_path, title=f"{name.upper()} Test Confusion Matrix")

    eval_result = {
        "name": name,
        "task": bundle.get("task", "attack_classification"),
        "version": bundle.get("version", "1.0.0"),
        "accuracy": round(acc, 4),
        "precision_macro": round(p_macro, 4),
        "recall_macro": round(r_macro, 4),
        "f1_macro": round(f1_macro, 4),
        "roc_auc": round(roc_auc, 4),
        "inference_latency_ms": inf_latency_ms,
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_png": str(cm_path.relative_to(REPO_ROOT)),
        "classes": classes,
        "test_samples": len(X_test),
    }

    # Write evaluation json
    eval_file = output_dir / f"{name}_evaluation.json"
    eval_file.write_text(json.dumps(eval_result, indent=2), encoding="utf-8")
    logger.info(
        "Evaluated %s: Acc=%.4f, Macro-F1=%.4f, ROC-AUC=%.4f, Latency=%.3fms",
        name,
        acc,
        f1_macro,
        roc_auc,
        inf_latency_ms,
    )
    return eval_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate intrusion detection models on test partition")
    parser.add_argument("--test-path", type=str, default="ml/data/cache/test.parquet")
    parser.add_argument("--models-dir", type=str, default="ml/models")
    args = parser.parse_args()

    test_file = REPO_ROOT / args.test_path
    models_dir = REPO_ROOT / args.models_dir

    if not test_file.exists():
        logger.error("Test partition %s not found. Run split.py first.", test_file)
        sys.exit(1)

    df_test = pd.read_parquet(test_file)
    validate_features(df_test[list(CANONICAL_FEATURES)])

    classifier_bundles = list(models_dir.glob("*.joblib"))
    # Exclude isolation_forest from multi-class classifier evaluate
    classifier_bundles = [p for p in classifier_bundles if "isolation_forest" not in p.name]

    evaluations: list[dict[str, Any]] = []
    for bundle_path in classifier_bundles:
        res = evaluate_classifier(bundle_path, df_test, models_dir)
        evaluations.append(res)

    print(f"\n[AdaptiveCloud ML] Successfully evaluated {len(evaluations)} classifier(s) on held-out test data.")


if __name__ == "__main__":
    main()
