"""
ml/tests/test_loaders.py
Tests for Dataset Loaders, Provenance Verification, and Parquet Caching.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from ml.loaders.base import BaseDatasetLoader, PROVENANCE_COLUMNS
from ml.loaders.cic_loader import CICDatasetLoader
from ml.loaders.kdd_loader import KDDDatasetLoader
from ml.loaders.live_loader import LiveDatasetLoader
from ml.loaders.unsw_loader import UNSWDatasetLoader


def test_provenance_validation(synthetic_cic_df: pd.DataFrame) -> None:
    loader = CICDatasetLoader()
    # Valid dataframe passes
    loader.validate_provenance(synthetic_cic_df)

    # Missing provenance column fails loudly
    broken = synthetic_cic_df.drop(columns=["row_id"])
    with pytest.raises(ValueError, match="violates provenance schema"):
        loader.validate_provenance(broken)


def test_feature_space_validation(synthetic_cic_df: pd.DataFrame) -> None:
    loader = CICDatasetLoader()
    loader.validate_features(synthetic_cic_df)

    # Missing feature fails loudly
    broken = synthetic_cic_df.drop(columns=["flow_duration"])
    with pytest.raises(ValueError, match="violates FS-CIC schema"):
        loader.validate_features(broken)


def test_parquet_caching(synthetic_cic_df: pd.DataFrame, tmp_cache_dir: Path) -> None:
    loader = CICDatasetLoader(cache_dir=tmp_cache_dir)
    cache_path = loader.save_cache(synthetic_cic_df, tag="test_tag")
    assert cache_path.exists()
    assert cache_path.suffix == ".parquet"

    loaded = loader.load_cache(tag="test_tag")
    assert loaded is not None
    assert len(loaded) == len(synthetic_cic_df)
    assert "flow_duration" in loaded.columns
    assert "row_id" in loaded.columns


def test_stratified_subsampling(synthetic_cic_df: pd.DataFrame) -> None:
    loader = CICDatasetLoader()
    sampled = loader.sample_stratified(synthetic_cic_df, fraction=0.50, random_state=42)
    assert len(sampled) < len(synthetic_cic_df)
    # Check all classes still present
    orig_classes = set(synthetic_cic_df["family"])
    sampled_classes = set(sampled["family"])
    assert orig_classes == sampled_classes


def test_live_loader_analyst_gate(tmp_path: Path) -> None:
    """Honesty Rule: Unverified live telemetry must be rejected from training sets."""
    feed_dir = tmp_path / "feedback"
    feed_dir.mkdir(parents=True, exist_ok=True)

    # Unverified file
    unverified_file = feed_dir / "unverified.parquet"
    df_unverified = pd.DataFrame({
        "flow_duration": [100.0],
        "verified": [False],
        "label": ["port_scan_recon"],
    })
    df_unverified.to_parquet(unverified_file, index=False)

    loader = LiveDatasetLoader(raw_dir=feed_dir, only_verified=True)
    df = loader.load_raw()
    assert len(df) == 0, "Unverified live events must NOT be loaded for training!"
