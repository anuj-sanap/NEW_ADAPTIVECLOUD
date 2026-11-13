"""
ml/tests/conftest.py
Pytest fixtures providing clean synthetic telemetry datasets for all 4 isolated feature spaces.
Strictly isolated within tests; never part of production runtime data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator
import numpy as np
import pandas as pd
import pytest

from ml.features.spaces import get_feature_space
from ml.loaders.base import PROVENANCE_COLUMNS


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def tmp_models_dir(tmp_path: Path) -> Path:
    d = tmp_path / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def synthetic_cic_df() -> pd.DataFrame:
    """Generates synthetic FS-CIC DataFrame for testing."""
    np.random.seed(42)
    space = get_feature_space("FS-CIC")
    n_rows = 100

    data = {feat: np.random.uniform(0.0, 1000.0, size=n_rows) for feat in space.features}
    df = pd.DataFrame(data)

    # Assign provenance
    df["dataset"] = "cic-ids2017"
    df["source_file"] = "synthetic_test.csv"
    df["row_id"] = [f"cic_{i}" for i in range(n_rows)]
    families = ["benign", "dos", "ddos", "brute_force", "port_scan_recon"]
    df["family"] = [families[i % len(families)] for i in range(n_rows)]
    df["original_label"] = df["family"]
    df["subtype"] = df["family"]
    df["l1"] = [0 if f == "benign" else 1 for f in df["family"]]
    df["split"] = "unassigned"

    return df


@pytest.fixture
def synthetic_unsw_df() -> pd.DataFrame:
    """Generates synthetic FS-UNSW DataFrame for testing."""
    np.random.seed(42)
    space = get_feature_space("FS-UNSW")
    n_rows = 80

    data = {feat: np.random.uniform(0.0, 500.0, size=n_rows) for feat in space.features}
    df = pd.DataFrame(data)

    df["dataset"] = "unsw-nb15"
    df["source_file"] = "synthetic_unsw.csv"
    df["row_id"] = [f"unsw_{i}" for i in range(n_rows)]
    families = ["benign", "port_scan_recon", "botnet", "dos", "exploit_other"]
    df["family"] = [families[i % len(families)] for i in range(n_rows)]
    df["original_label"] = df["family"]
    df["subtype"] = df["family"]
    df["l1"] = [0 if f == "benign" else 1 for f in df["family"]]
    df["split"] = "unassigned"

    return df


@pytest.fixture
def synthetic_kdd_df() -> pd.DataFrame:
    """Generates synthetic FS-KDD DataFrame for testing."""
    np.random.seed(42)
    space = get_feature_space("FS-KDD")
    n_rows = 60

    data = {feat: np.random.uniform(0.0, 100.0, size=n_rows) for feat in space.features}
    df = pd.DataFrame(data)

    df["dataset"] = "nsl-kdd"
    df["source_file"] = "synthetic_kdd.csv"
    df["row_id"] = [f"kdd_{i}" for i in range(n_rows)]
    families = ["benign", "dos", "infiltration", "brute_force"]
    df["family"] = [families[i % len(families)] for i in range(n_rows)]
    df["original_label"] = df["family"]
    df["subtype"] = df["family"]
    df["l1"] = [0 if f == "benign" else 1 for f in df["family"]]
    df["split"] = "unassigned"

    return df


@pytest.fixture
def synthetic_live_df() -> pd.DataFrame:
    """Generates synthetic FS-LIVE DataFrame for testing."""
    np.random.seed(42)
    space = get_feature_space("FS-LIVE")
    n_rows = 50

    data = {feat: np.random.uniform(0.0, 200.0, size=n_rows) for feat in space.features}
    df = pd.DataFrame(data)

    df["dataset"] = "live_cloud_events"
    df["source_file"] = "agent_stream.parquet"
    df["row_id"] = [f"live_{i}" for i in range(n_rows)]
    df["family"] = "benign"
    df["original_label"] = "normal"
    df["subtype"] = "normal"
    df["l1"] = 0
    df["split"] = "unassigned"
    df["verified"] = True
    df["analyst_id"] = "analyst_sec_01"

    return df
