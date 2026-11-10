"""
ml/training/split.py
Stratified dataset partitioning for training, validation, and held-out test sets.
Also produces benign-only partition for unsupervised anomaly detection.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.feature_map import CANONICAL_FEATURES, validate_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("split")


def split_data(
    input_file: Path,
    output_dir: Path,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(input_file)
    logger.info("Loaded preprocessed dataset (%d rows) from %s", len(df), input_file)

    validate_features(df[list(CANONICAL_FEATURES)])

    # First split: Train+Val (85%), Test (15%)
    train_val_df, test_df = train_test_split(
        df,
        test_size=test_size,
        stratify=df["label"],
        random_state=random_state,
    )

    # Second split: Train (70%), Val (15%) -> val_ratio relative to train_val
    relative_val_size = val_size / (1.0 - test_size)
    train_df, val_df = train_test_split(
        train_val_df,
        test_size=relative_val_size,
        stratify=train_val_df["label"],
        random_state=random_state,
    )

    # Benign-only train slice for unsupervised Isolation Forest
    benign_train_df = train_df[train_df["label"] == "benign"].copy()

    # Paths
    train_path = output_dir / "train.parquet"
    val_path = output_dir / "val.parquet"
    test_path = output_dir / "test.parquet"
    benign_path = output_dir / "benign_train.parquet"

    train_df.to_parquet(train_path, index=False)
    val_df.to_parquet(val_path, index=False)
    test_df.to_parquet(test_path, index=False)
    benign_train_df.to_parquet(benign_path, index=False)

    logger.info("Split completed:")
    logger.info("  Train:        %d rows -> %s", len(train_df), train_path.name)
    logger.info("  Validation:   %d rows -> %s", len(val_df), val_path.name)
    logger.info("  Test:         %d rows -> %s", len(test_df), test_path.name)
    logger.info("  Benign Train: %d rows -> %s", len(benign_train_df), benign_path.name)

    return {
        "train": train_path,
        "val": val_path,
        "test": test_path,
        "benign_train": benign_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stratified dataset splitter")
    parser.add_argument("--input", type=str, default="ml/data/cache/flows_preprocessed.parquet")
    parser.add_argument("--output-dir", type=str, default="ml/data/cache")
    parser.add_argument("--test-size", type=float, default=0.15)
    parser.add_argument("--val-size", type=float, default=0.15)
    args = parser.parse_args()

    input_file = REPO_ROOT / args.input
    output_dir = REPO_ROOT / args.output_dir

    if not input_file.exists():
        logger.error("Input file %s does not exist", input_file)
        sys.exit(1)

    split_data(input_file, output_dir, args.test_size, args.val_size)


if __name__ == "__main__":
    main()

