"""
ml/training/preprocess.py
Data cleaning, anomaly/infinity handling, deduplication, and attack label unification.
Unifies diverse raw intrusion labels into AdaptiveCloud's canonical set:
benign, brute_force, ddos, port_scan.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preprocess")

# Mapping raw intrusion dataset labels to AdaptiveCloud canonical attack labels
LABEL_UNIFICATION_MAP: dict[str, str] = {
    # Benign variations
    "benign": "benign",
    "normal": "benign",
    # Brute Force variations
    "ftp-patator": "brute_force",
    "ssh-patator": "brute_force",
    "brute force -web": "brute_force",
    "brute force -xss": "brute_force",
    "bruteforce": "brute_force",
    # DDoS / DoS variations
    "ddos": "ddos",
    "dos hulk": "ddos",
    "dos goldeneye": "ddos",
    "dos slowloris": "ddos",
    "dos slowhttptest": "ddos",
    "heartbleed": "ddos",
    # PortScan variations
    "portscan": "port_scan",
    "port_scan": "port_scan",
    "reconnaissance": "port_scan",
}


def clean_and_unify(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans numerical columns (handling inf, -inf, NaN), removes duplicates,
    standardizes attack labels, and enforces canonical feature alignment.
    """
    initial_rows = len(df)
    logger.info("Starting preprocessing with %d rows ...", initial_rows)

    # 1. Standardize label column name and values
    if "Label" in df.columns and "label" not in df.columns:
        df = df.rename(columns={"Label": "label"})

    if "label" not in df.columns:
        raise ValueError("Dataset does not contain a 'label' column")

    # Unify labels
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df["label"] = df["label"].map(lambda x: LABEL_UNIFICATION_MAP.get(x, x))

    # Keep only supported network attack classes
    supported_classes = {"benign", "brute_force", "ddos", "port_scan"}
    df = df[df["label"].isin(supported_classes)].copy()
    logger.info("Filtered to supported network classes (%s): %d rows remain", supported_classes, len(df))

    # 2. Select only canonical features + label
    missing_feats = [f for f in CANONICAL_FEATURES if f not in df.columns]
    if missing_feats:
        raise ValueError(f"Missing canonical features before preprocessing: {missing_feats}")

    cols_to_keep = list(CANONICAL_FEATURES) + ["label"]
    df = df[cols_to_keep].copy()

    # 3. Replace inf and -inf with NaN across all numeric features
    numeric_cols = list(CANONICAL_FEATURES)
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    # 4. Drop NaN and duplicate records
    nan_count = df[numeric_cols].isna().any(axis=1).sum()
    if nan_count > 0:
        logger.info("Dropping %d rows containing NaN / Inf values", nan_count)
        df = df.dropna(subset=numeric_cols).copy()

    dup_count = df.duplicated(subset=numeric_cols).sum()
    if dup_count > 0:
        logger.info("Dropping %d duplicate feature rows", dup_count)
        df = df.drop_duplicates(subset=numeric_cols).copy()

    validate_features(df[list(CANONICAL_FEATURES)])
    logger.info(
        "Preprocessing complete: %d valid rows retained (label distribution:\n%s)",
        len(df),
        df["label"].value_counts().to_string(),
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess flow dataset")
    parser.add_argument("--input", type=str, default="ml/data/cache/flows_sampled.parquet")
    parser.add_argument("--output", type=str, default="ml/data/cache/flows_preprocessed.parquet")
    args = parser.parse_args()

    input_path = REPO_ROOT / args.input
    output_path = REPO_ROOT / args.output

    if not input_path.exists():
        logger.error("Input file %s does not exist. Run download_data.py first.", input_path)
        sys.exit(1)

    df_raw = pd.read_parquet(input_path)
    df_clean = clean_and_unify(df_raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(output_path, index=False)
    print(f"[AdaptiveCloud ML] Preprocessed dataset written to: {output_path}")


if __name__ == "__main__":
    main()

