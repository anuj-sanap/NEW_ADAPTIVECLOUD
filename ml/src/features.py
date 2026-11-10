"""
ml/src/features.py
Feature extraction from MetricPayload dicts.
Keeps feature list in sync with docs/DATA_SCHEMA.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ── Canonical feature order ───────────────────────────────────────────────────
# This list is the authoritative feature set. Any change here MUST be reflected
# in model retraining — a mismatch will cause silent mis-predictions.
FEATURE_NAMES: list[str] = [
    "cpu_percent",
    "memory_percent",
    "memory_used_mb",
    "disk_read_bytes_sec",
    "disk_write_bytes_sec",
    "net_bytes_sent_sec",
    "net_bytes_recv_sec",
    "active_connections",
    "process_count",
    "event_log_errors_1m",
    "event_log_warnings_1m",
]

LABEL_CLASSES: list[str] = [
    "benign",
    "brute_force",
    "ddos",
    "port_scan",
    "unauthorized_access",
    "suspicious_process",
]


def extract_features(payload: dict) -> np.ndarray:
    """
    Extract the feature vector from a MetricPayload dict.

    Args:
        payload: Dict matching the MetricPayload schema.

    Returns:
        1-D numpy array of shape (len(FEATURE_NAMES),).

    Raises:
        KeyError: if a required field is missing from payload.
        ValueError: if any feature value cannot be cast to float.
    """
    values: list[float] = []
    for name in FEATURE_NAMES:
        raw = payload.get(name)
        if raw is None:
            raise KeyError(f"Missing feature '{name}' in payload")
        values.append(float(raw))
    return np.array(values, dtype=np.float32)


def payloads_to_dataframe(payloads: list[dict]) -> pd.DataFrame:
    """
    Convert a list of MetricPayload dicts to a DataFrame with canonical feature columns.
    Drops rows where any feature is null.
    """
    rows = []
    for p in payloads:
        try:
            rows.append({name: float(p[name]) for name in FEATURE_NAMES})
        except (KeyError, TypeError, ValueError):
            continue  # Skip malformed rows

    df = pd.DataFrame(rows, columns=FEATURE_NAMES)
    return df.dropna()
