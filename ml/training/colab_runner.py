"""
ml/training/colab_runner.py
Standalone training orchestrator optimized for Google Colab (Free Tier) & Local Windows.
Features:
- Auto-detects CUDA / GPU for XGBoost and LightGBM acceleration.
- Stratified sampling (default 10%) to fit Colab RAM and finish in minutes.
- Evaluates Random Forest, XGBoost, and LightGBM across feature spaces.
- Saves models, metadata, and evaluation plots to Google Drive or local models/ directory.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.loaders.cic_loader import CICDatasetLoader
from ml.training.trainer import ModelTrainer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("colab_runner")


def check_gpu() -> bool:
    """Checks for GPU availability via PyTorch or environment."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("CUDA GPU detected: %s", torch.cuda.get_device_name(0))
            return True
    except ImportError:
        pass
    logger.info("No CUDA GPU detected; running in optimized CPU multi-core mode.")
    return False


def run_pipeline(
    sample_fraction: float = 0.10,
    feature_space: str = "FS-CIC",
    output_dir: Path = REPO_ROOT / "ml" / "models",
) -> None:
    has_gpu = check_gpu()
    logger.info(
        "Initiating Colab Runner [Space: %s, Sample: %.1f%%, GPU: %s]",
        feature_space,
        sample_fraction * 100,
        has_gpu,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    logger.info("Loading dataset for %s...", feature_space)
    loader = CICDatasetLoader()
    df = loader.load(sample_fraction=sample_fraction, use_cache=True)

    if df.empty:
        logger.warning(
            "Dataset is empty. Ensure raw data or synthetic test fixtures exist in ml/data/raw."
        )
        return

    logger.info("Loaded %d rows with features: %s", len(df), loader.expected_features[:5])

    # 2. Split
    from sklearn.model_selection import train_test_split
    strat_col = "family" if "family" in df.columns else "label"
    df_train, df_val = train_test_split(
        df,
        test_size=0.2,
        stratify=df[strat_col],
        random_state=42,
    )

    # 3. Train models
    trainer = ModelTrainer(feature_space=feature_space, output_dir=output_dir)
    for model_name in ["random_forest", "xgboost", "lightgbm"]:
        logger.info("Training %s on %s...", model_name, feature_space)
        meta = trainer.train_model(
            model_name=model_name,
            df_train=df_train,
            df_val=df_val,
            label_col=strat_col,
        )
        logger.info("Finished %s: Macro F1 = %.4f", model_name, meta["macro_f1"])

    logger.info("All models trained and saved to %s", output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Colab / Local ML Runner")
    parser.add_argument("--sample-fraction", type=float, default=0.10, help="Stratified sample fraction (default: 0.10)")
    parser.add_argument("--space", type=str, default="FS-CIC", help="Target feature space (FS-CIC, FS-UNSW, FS-KDD)")
    parser.add_argument("--output-dir", type=str, default="ml/models", help="Output directory for trained models")
    args = parser.parse_args()

    run_pipeline(
        sample_fraction=args.sample_fraction,
        feature_space=args.space,
        output_dir=REPO_ROOT / args.output_dir,
    )


if __name__ == "__main__":
    main()
