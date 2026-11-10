"""
ml/learning/drift.py
Statistical drift detection engine for network flow and telemetry feature streams.
Implements:
1. Population Stability Index (PSI) per feature.
2. Two-sample Kolmogorov-Smirnov (KS) goodness-of-fit test per feature.
3. Prediction confidence and rolling feedback accuracy drift tracking.
"""
from __future__ import annotations

import logging
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("ml.learning.drift")


def calculate_psi(
    reference: np.ndarray,
    current: np.ndarray,
    num_buckets: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Computes Population Stability Index (PSI) between reference baseline and current stream:
        PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
    Interpretation:
        PSI < 0.10: No significant drift (stable)
        0.10 <= PSI < 0.25: Moderate drift / warning
        PSI >= 0.25: Significant concept/data drift (retraining warranted)
    """
    ref = np.asarray(reference, dtype=np.float64).flatten()
    curr = np.asarray(current, dtype=np.float64).flatten()

    ref = ref[np.isfinite(ref)]
    curr = curr[np.isfinite(curr)]

    if len(ref) == 0 or len(curr) == 0:
        return 0.0

    # Determine quantile bins based on reference distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bins = np.percentile(ref, percentiles)
    bins = np.unique(bins)

    if len(bins) < 2:
        # Constant reference value
        return 0.0 if np.allclose(ref.mean(), curr.mean(), atol=1e-3) else 1.0

    # Ensure infinite boundaries for edge values
    bins[0] = -np.inf
    bins[-1] = np.inf

    # Histogram counts
    ref_counts, _ = np.histogram(ref, bins=bins)
    curr_counts, _ = np.histogram(curr, bins=bins)

    ref_pct = ref_counts / len(ref)
    curr_pct = curr_counts / len(curr)

    # Apply epsilon smoothing to prevent div by zero and log(0)
    ref_pct = np.clip(ref_pct, epsilon, 1.0)
    curr_pct = np.clip(curr_pct, epsilon, 1.0)

    # Renormalize
    ref_pct /= np.sum(ref_pct)
    curr_pct /= np.sum(curr_pct)

    psi_val = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
    return float(max(0.0, psi_val))


def calculate_ks(reference: np.ndarray, current: np.ndarray) -> tuple[float, float]:
    """
    Two-sample Kolmogorov-Smirnov test to detect non-parametric distribution divergence.
    Returns (ks_statistic, p_value).
    """
    ref = np.asarray(reference, dtype=np.float64).flatten()
    curr = np.asarray(current, dtype=np.float64).flatten()

    ref = ref[np.isfinite(ref)]
    curr = curr[np.isfinite(curr)]

    if len(ref) < 2 or len(curr) < 2:
        return 0.0, 1.0

    res = stats.ks_2samp(ref, curr)
    return float(res.statistic), float(res.pvalue)


def evaluate_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    psi_threshold: float = 0.25,
    ks_alpha: float = 0.05,
) -> dict[str, Any]:
    """
    Evaluates multi-feature drift across baseline and current dataframes.
    Returns composite summary and per-feature diagnostics.
    """
    if feature_cols is None:
        feature_cols = [c for c in reference_df.columns if c in current_df.columns and pd.api.types.is_numeric_dtype(reference_df[c])]

    results: dict[str, dict[str, Any]] = {}
    drifted_features: list[str] = []
    psi_scores: list[float] = []

    for col in feature_cols:
        if col not in reference_df.columns or col not in current_df.columns:
            continue

        ref_vals = reference_df[col].dropna().values
        curr_vals = current_df[col].dropna().values

        if len(ref_vals) < 5 or len(curr_vals) < 5:
            continue

        psi = calculate_psi(ref_vals, curr_vals)
        ks_stat, p_val = calculate_ks(ref_vals, curr_vals)

        is_drift = (psi >= psi_threshold) or (p_val < ks_alpha and ks_stat > 0.20)
        if is_drift:
            drifted_features.append(col)
        psi_scores.append(psi)

        results[col] = {
            "psi": round(psi, 4),
            "ks_statistic": round(ks_stat, 4),
            "p_value": round(p_val, 5),
            "is_drift": bool(is_drift),
        }

    mean_psi = float(np.mean(psi_scores)) if psi_scores else 0.0
    max_psi = float(np.max(psi_scores)) if psi_scores else 0.0
    overall_drift = len(drifted_features) > 0 and (max_psi >= psi_threshold)

    return {
        "overall_drift": overall_drift,
        "mean_psi": round(mean_psi, 4),
        "max_psi": round(max_psi, 4),
        "drifted_features_count": len(drifted_features),
        "drifted_features": drifted_features,
        "total_features_evaluated": len(results),
        "feature_metrics": results,
    }

