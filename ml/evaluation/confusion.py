"""
ml/evaluation/confusion.py
Confusion Matrix extraction and plot generation for threat classification models.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

logger = logging.getLogger("ml.evaluation.confusion")


def generate_confusion_matrix(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    class_names: List[str],
    output_png: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Computes raw confusion matrix and saves an annotated heatmap PNG.
    """
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    matrix_list = cm.tolist()

    result: Dict[str, Any] = {
        "labels": class_names,
        "matrix": matrix_list,
    }

    if output_png:
        output_png.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.figure.colorbar(im, ax=ax)

        ax.set(
            xticks=np.arange(cm.shape[1]),
            yticks=np.arange(cm.shape[0]),
            xticklabels=class_names,
            yticklabels=class_names,
            ylabel="True Label",
            xlabel="Predicted Label",
            title="Confusion Matrix",
        )

        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Loop over data dimensions and create text annotations
        thresh = cm.max() / 2.0 if cm.max() > 0 else 1.0
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
        fig.savefig(output_png)
        plt.close(fig)
        result["png_path"] = str(output_png)
        logger.info("Saved confusion matrix heatmap to %s", output_png)

    return result
