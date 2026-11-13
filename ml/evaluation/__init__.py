"""
ml/evaluation package.
Metrics computation, confusion matrices, and cross-model benchmarking.
"""
from ml.evaluation.benchmark import BenchmarkRunner
from ml.evaluation.confusion import generate_confusion_matrix
from ml.evaluation.metrics import compute_classification_metrics

__all__ = [
    "compute_classification_metrics",
    "generate_confusion_matrix",
    "BenchmarkRunner",
]
