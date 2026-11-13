"""
ml/loaders/live_loader.py
Dataset Loader for FS-LIVE (Live Agent Telemetry & Human-in-the-Loop Feedback Store).
HONESTY & SAFETY RULE: Live cloud events are NEVER used for training unless explicitly
validated and signed off by a security analyst.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from ml.loaders.base import BaseDatasetLoader, PROVENANCE_COLUMNS
from ml.taxonomy.mapper import TaxonomyMapper

logger = logging.getLogger("ml.loaders.live")


class LiveDatasetLoader(BaseDatasetLoader):
    """
    Loader for Live Agent Telemetry adhering to FS-LIVE.
    Enforces the analyst validation gate: unverified live events cannot enter training sets.
    """

    def __init__(
        self,
        dataset_name: str = "live_cloud_events",
        raw_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        mapper: Optional[TaxonomyMapper] = None,
        only_verified: bool = True,
    ) -> None:
        super().__init__(
            dataset_name=dataset_name,
            feature_space="FS-LIVE",
            raw_dir=raw_dir or (Path(__file__).resolve().parent.parent / "data" / "live_feedback"),
            cache_dir=cache_dir,
            mapper=mapper,
        )
        self.only_verified = only_verified

    def load_raw(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Loads verified analyst feedback records or raw live telemetry.
        If only_verified=True, strictly filters for rows with verified=True and analyst_id present.
        """
        if not self.raw_dir.exists():
            self.raw_dir.mkdir(parents=True, exist_ok=True)

        parquet_files = sorted(list(self.raw_dir.glob("*.parquet")))
        csv_files = sorted(list(self.raw_dir.glob("*.csv")))
        all_files = parquet_files + csv_files

        if not all_files:
            logger.info("No live feedback files found in %s", self.raw_dir)
            return pd.DataFrame(columns=self.expected_features + PROVENANCE_COLUMNS)

        records: List[pd.DataFrame] = []
        rows_so_far = 0

        for file_path in all_files:
            if max_rows and rows_so_far >= max_rows:
                break

            if file_path.suffix == ".parquet":
                df_raw = pd.read_parquet(file_path, engine="pyarrow")
            else:
                df_raw = pd.read_csv(file_path, low_memory=False, encoding="utf-8")

            # Analyst validation gate
            if self.only_verified:
                if "verified" in df_raw.columns:
                    df_raw = df_raw[df_raw["verified"] == True]
                else:
                    # File does not have verification metadata; skip for training safety
                    logger.warning(
                        "File %s lacks 'verified' flag. Skipping unverified live telemetry.",
                        file_path.name,
                    )
                    continue

                if "analyst_id" in df_raw.columns:
                    df_raw = df_raw[df_raw["analyst_id"].notna() & (df_raw["analyst_id"] != "")]
                else:
                    logger.warning(
                        "File %s lacks 'analyst_id'. Skipping unverified live telemetry.",
                        file_path.name,
                    )
                    continue

            if df_raw.empty:
                continue

            # Identify labels: analyst ground truth overrides prediction
            if "ground_truth" in df_raw.columns:
                raw_labels = df_raw["ground_truth"].astype(str)
            elif "label" in df_raw.columns:
                raw_labels = df_raw["label"].astype(str)
            else:
                raw_labels = pd.Series(["benign"] * len(df_raw))

            df_features = pd.DataFrame(index=df_raw.index)
            for feat in self.expected_features:
                if feat in df_raw.columns:
                    series = pd.to_numeric(df_raw[feat], errors="coerce")
                    series = series.replace([np.inf, -np.inf], np.nan)
                    median_val = series.median() if not np.isnan(series.median()) else 0.0
                    df_features[feat] = series.fillna(median_val)
                else:
                    df_features[feat] = 0.0

            provenance = pd.DataFrame(index=df_raw.index)
            provenance["dataset"] = self.dataset_name
            provenance["source_file"] = file_path.name
            if "row_id" in df_raw.columns:
                provenance["row_id"] = df_raw["row_id"].astype(str)
            elif "event_id" in df_raw.columns:
                provenance["row_id"] = df_raw["event_id"].astype(str)
            else:
                provenance["row_id"] = [f"{file_path.stem}_{rows_so_far + i}" for i in range(len(df_raw))]

            provenance["original_label"] = raw_labels

            mapped = [self.mapper.map_label("live", lbl) for lbl in raw_labels]
            provenance["family"] = [m[0] for m in mapped]
            provenance["subtype"] = [m[1] for m in mapped]
            provenance["l1"] = [m[2] for m in mapped]
            provenance["split"] = "unassigned"

            combined = pd.concat([df_features, provenance], axis=1)
            records.append(combined)
            rows_so_far += len(combined)

            if max_rows and rows_so_far >= max_rows:
                break

        if not records:
            return pd.DataFrame(columns=self.expected_features + PROVENANCE_COLUMNS)

        full_df = pd.concat(records, ignore_index=True)
        if max_rows:
            full_df = full_df.iloc[:max_rows].reset_index(drop=True)

        return full_df
