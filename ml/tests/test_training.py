"""
ml/tests/test_training.py
Tests for Multi-Model Training Orchestrator and Benchmarking.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from ml.evaluation.benchmark import BenchmarkRunner
from ml.training.trainer import ModelTrainer


def test_model_trainer_pipeline(synthetic_cic_df: pd.DataFrame, tmp_models_dir: Path) -> None:
    # 80/20 train/val split
    n = len(synthetic_cic_df)
    train_df = synthetic_cic_df.iloc[: int(n * 0.8)].copy()
    val_df = synthetic_cic_df.iloc[int(n * 0.8) :].copy()

    trainer = ModelTrainer(feature_space="FS-CIC", output_dir=tmp_models_dir, random_state=42)

    # 1. Random Forest
    rf_meta = trainer.train_model("random_forest", train_df, val_df, label_col="family")
    assert rf_meta["model_name"] == "random_forest"
    assert "macro_f1" in rf_meta
    assert (tmp_models_dir / "random_forest_fs-cic.joblib").exists()

    # 2. XGBoost
    xgb_meta = trainer.train_model("xgboost", train_df, val_df, label_col="family")
    assert xgb_meta["model_name"] == "xgboost"
    assert (tmp_models_dir / "xgboost_fs-cic.joblib").exists()

    # 3. LightGBM
    lgbm_meta = trainer.train_model("lightgbm", train_df, val_df, label_col="family")
    assert lgbm_meta["model_name"] == "lightgbm"
    assert (tmp_models_dir / "lightgbm_fs-cic.joblib").exists()

    # 4. Benchmark Runner
    bench = BenchmarkRunner(models_dir=tmp_models_dir)
    res = bench.run_benchmark()
    assert res["evaluated_models_count"] >= 3
    assert "champion_candidate" in res
