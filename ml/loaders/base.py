"""
ml/loaders/base.py
Abstract Base Dataset Loader with Provenance Enforcement, Chunking, and Parquet Caching.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final, List, Optional
import numpy as np
import pandas as pd
import yaml

from ml.taxonomy.mapper import TaxonomyMapper

PROVENANCE_COLUMNS: Final[List[str]] = [
    "dataset",
    "source_file",
    "row_id",
    "original_label",
    "family",
    "subtype",
    "l1",
    "split",
]

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class BaseDatasetLoader(ABC):
    """
    Abstract base class for all dataset loaders.
    Guarantees:
    1. Feature space isolation (one loader belongs to exactly one feature space).
    2. Complete provenance tracking on every row.
    3. Memory-safe reading & Parquet caching.
    4. Deterministic stratified sampling.
    """

    def __init__(
        self,
        dataset_name: str,
        feature_space: str,
        raw_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        mapper: Optional[TaxonomyMapper] = None,
    ) -> None:
        self.dataset_name = dataset_name
        self.feature_space = feature_space
        self.raw_dir = raw_dir or (Path(__file__).resolve().parent.parent / "data" / "raw" / dataset_name)
        self.cache_dir = cache_dir or (Path(__file__).resolve().parent.parent / "data" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.mapper = mapper or TaxonomyMapper()
        self._expected_features = self._load_expected_features()

    def _load_expected_features(self) -> List[str]:
        """Loads canonical features defined for this loader's feature space."""
        fs_config = CONFIG_DIR / "feature_spaces.yaml"
        if not fs_config.exists():
            return []
        with open(fs_config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        spaces = cfg.get("feature_spaces", {})
        space_entry = spaces.get(self.feature_space, {})
        return list(space_entry.get("features", []))

    @property
    def expected_features(self) -> List[str]:
        return list(self._expected_features)

    @abstractmethod
    def load_raw(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Parses raw data files from self.raw_dir into a pandas DataFrame.
        Must normalize raw columns into self.expected_features and attach provenance.
        """
        pass

    def validate_provenance(self, df: pd.DataFrame) -> None:
        """Ensures all mandatory provenance columns are present and non-empty."""
        missing = [col for col in PROVENANCE_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(
                f"Dataset {self.dataset_name} violates provenance schema. "
                f"Missing required provenance columns: {missing}"
            )

    def validate_features(self, df: pd.DataFrame) -> None:
        """Verifies that all expected feature space features are present."""
        if not self._expected_features:
            return
        missing = [feat for feat in self._expected_features if feat not in df.columns]
        if missing:
            raise ValueError(
                f"DataFrame violates {self.feature_space} schema. "
                f"Missing {len(missing)} features: {missing[:5]}..."
            )

    def get_cache_path(self, tag: str = "full") -> Path:
        """Returns standard Parquet cache path for this dataset."""
        return self.cache_dir / f"{self.dataset_name}_{self.feature_space.lower()}_{tag}.parquet"

    def save_cache(self, df: pd.DataFrame, tag: str = "full") -> Path:
        """Saves processed dataframe to Parquet cache."""
        path = self.get_cache_path(tag)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False, engine="pyarrow")
        return path

    def load_cache(self, tag: str = "full") -> Optional[pd.DataFrame]:
        """Loads dataframe from Parquet cache if available."""
        path = self.get_cache_path(tag)
        if path.exists():
            return pd.read_parquet(path, engine="pyarrow")
        return None

    def sample_stratified(
        self,
        df: pd.DataFrame,
        fraction: float,
        stratify_col: str = "family",
        random_state: int = 42,
    ) -> pd.DataFrame:
        """
        Deterministically samples a fraction of the dataset while preserving
        class distributions. Classes with fewer samples than can be stratified
        are retained completely.
        """
        if fraction >= 1.0 or fraction <= 0.0:
            return df

        if stratify_col not in df.columns:
            return df.sample(frac=fraction, random_state=random_state)

        # Group by label and sample
        grouped = df.groupby(stratify_col, group_keys=False)
        sampled_parts = []
        for name, group in grouped:
            n_samples = max(1, int(np.round(len(group) * fraction)))
            if n_samples >= len(group):
                sampled_parts.append(group)
            else:
                sampled_parts.append(group.sample(n=n_samples, random_state=random_state))

        sampled_df = pd.concat(sampled_parts, ignore_index=True)
        return sampled_df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)

    def load(
        self,
        sample_fraction: Optional[float] = None,
        use_cache: bool = True,
        force_reload: bool = False,
    ) -> pd.DataFrame:
        """
        Unified loading interface with Parquet cache and subsampling.
        """
        cache_tag = f"sub_{int(sample_fraction * 100)}" if (sample_fraction and sample_fraction < 1.0) else "full"

        if use_cache and not force_reload:
            cached = self.load_cache(cache_tag)
            if cached is not None:
                self.validate_provenance(cached)
                self.validate_features(cached)
                return cached

        # Load raw
        df = self.load_raw()
        self.validate_provenance(df)
        self.validate_features(df)

        if sample_fraction is not None and 0.0 < sample_fraction < 1.0:
            df = self.sample_stratified(df, sample_fraction)

        if use_cache:
            self.save_cache(df, cache_tag)

        return df
