"""
ml/loaders/unsw_loader.py
Dataset Loader for FS-UNSW (UNSW-NB15).
Enforces feature space isolation for UNSW-NB15, tracks full provenance,
and translates raw attack categories to canonical families.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from ml.loaders.base import BaseDatasetLoader, PROVENANCE_COLUMNS
from ml.taxonomy.mapper import TaxonomyMapper

logger = logging.getLogger("ml.loaders.unsw")


class UNSWDatasetLoader(BaseDatasetLoader):
    """
    Loader for UNSW-NB15 dataset strictly adhering to FS-UNSW.
    """

    def __init__(
        self,
        dataset_name: str = "unsw-nb15",
        raw_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        mapper: Optional[TaxonomyMapper] = None,
    ) -> None:
        super().__init__(
            dataset_name=dataset_name,
            feature_space="FS-UNSW",
            raw_dir=raw_dir,
            cache_dir=cache_dir,
            mapper=mapper,
        )

    def load_raw(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Parses raw UNSW-NB15 CSV files into FS-UNSW representation.
        """
        if not self.raw_dir.exists():
            self.raw_dir.mkdir(parents=True, exist_ok=True)

        csv_files = sorted(list(self.raw_dir.glob("*.csv")))
        if not csv_files:
            logger.warning("No CSV files found in %s for %s", self.raw_dir, self.dataset_name)
            return pd.DataFrame(columns=self.expected_features + PROVENANCE_COLUMNS)

        records: List[pd.DataFrame] = []
        rows_so_far = 0

        for file_path in csv_files:
            if max_rows and rows_so_far >= max_rows:
                break

            logger.info("Reading UNSW file %s...", file_path.name)
            chunk_size = 50_000
            for chunk in pd.read_csv(
                file_path,
                chunksize=chunk_size,
                low_memory=False,
                encoding="utf-8",
                on_bad_lines="skip",
            ):
                chunk.columns = [c.strip().lower() for c in chunk.columns]

                # Identify label column (usually attack_cat or label)
                if "attack_cat" in chunk.columns:
                    raw_labels = chunk["attack_cat"].fillna("Normal").astype(str).str.strip()
                elif "label" in chunk.columns:
                    raw_labels = chunk["label"].apply(lambda v: "Attack" if str(v).strip() in ("1", "1.0") else "Normal")
                else:
                    raw_labels = pd.Series(["Normal"] * len(chunk))

                df_features = pd.DataFrame(index=chunk.index)
                for feat in self.expected_features:
                    col_key = feat.lower()
                    if col_key in chunk.columns:
                        series = pd.to_numeric(chunk[col_key], errors="coerce")
                        series = series.replace([np.inf, -np.inf], np.nan)
                        median_val = series.median() if not np.isnan(series.median()) else 0.0
                        df_features[feat] = series.fillna(median_val)
                    else:
                        df_features[feat] = 0.0

                provenance = pd.DataFrame(index=chunk.index)
                provenance["dataset"] = self.dataset_name
                provenance["source_file"] = file_path.name
                provenance["row_id"] = [f"{file_path.stem}_{rows_so_far + i}" for i in range(len(chunk))]
                provenance["original_label"] = raw_labels

                mapped = [self.mapper.map_label("unsw", lbl) for lbl in raw_labels]
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
