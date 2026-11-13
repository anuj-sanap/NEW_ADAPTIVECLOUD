"""
ml/loaders/cic_loader.py
Dataset Loader for FS-CIC (CIC-IDS2017 & CSE-CIC-IDS2018).
Extracts exactly 28 canonical flow features, applies provenance tracking,
cleans inf/nan, and translates raw labels to the 10 canonical families.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from ml.features.feature_map import CICIDS2017_MAP, CICIDS2018_MAP
from ml.loaders.base import BaseDatasetLoader, PROVENANCE_COLUMNS
from ml.taxonomy.mapper import TaxonomyMapper

logger = logging.getLogger("ml.loaders.cic")


class CICDatasetLoader(BaseDatasetLoader):
    """
    Loader for CIC-IDS2017 and CSE-CIC-IDS2018 datasets belonging to FS-CIC.
    """

    def __init__(
        self,
        dataset_name: str = "cic-ids2017",
        raw_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        mapper: Optional[TaxonomyMapper] = None,
    ) -> None:
        super().__init__(
            dataset_name=dataset_name,
            feature_space="FS-CIC",
            raw_dir=raw_dir,
            cache_dir=cache_dir,
            mapper=mapper,
        )

    def load_raw(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Parses raw CSV files from raw_dir, standardizes columns to FS-CIC,
        cleans inf/NaN, attaches provenance, and maps taxonomy labels.
        """
        if not self.raw_dir.exists():
            self.raw_dir.mkdir(parents=True, exist_ok=True)

        csv_files = sorted(list(self.raw_dir.glob("*.csv")))
        if not csv_files:
            logger.warning("No CSV files found in %s for %s", self.raw_dir, self.dataset_name)
            return pd.DataFrame(columns=self.expected_features + PROVENANCE_COLUMNS)

        records: List[pd.DataFrame] = []
        rows_so_far = 0

        mapping = CICIDS2017_MAP if "2017" in self.dataset_name else CICIDS2018_MAP

        for file_path in csv_files:
            if max_rows and rows_so_far >= max_rows:
                break

            logger.info("Reading %s...", file_path.name)
            # Read in chunks to prevent OOM
            chunk_size = 50_000
            for chunk in pd.read_csv(
                file_path,
                chunksize=chunk_size,
                low_memory=False,
                encoding="utf-8",
                on_bad_lines="skip",
            ):
                # Clean header whitespace
                chunk.columns = [c.strip() for c in chunk.columns]

                # Map column names
                rename_map = {orig: target for orig, target in mapping.items() if orig in chunk.columns}
                chunk = chunk.rename(columns=rename_map)

                if "label" not in chunk.columns and "Label" in chunk.columns:
                    chunk = chunk.rename(columns={"Label": "label"})

                raw_labels = chunk["label"].astype(str) if "label" in chunk.columns else pd.Series(["BENIGN"] * len(chunk))

                # Keep required features, filling missing with 0.0
                df_features = pd.DataFrame(index=chunk.index)
                for feat in self.expected_features:
                    if feat in chunk.columns:
                        series = pd.to_numeric(chunk[feat], errors="coerce")
                        series = series.replace([np.inf, -np.inf], np.nan)
                        median_val = series.median() if not np.isnan(series.median()) else 0.0
                        df_features[feat] = series.fillna(median_val)
                    else:
                        df_features[feat] = 0.0

                # Provenance
                provenance = pd.DataFrame(index=chunk.index)
                provenance["dataset"] = self.dataset_name
                provenance["source_file"] = file_path.name
                provenance["row_id"] = [f"{file_path.stem}_{rows_so_far + i}" for i in range(len(chunk))]
                provenance["original_label"] = raw_labels

                # Map taxonomy
                mapped = [self.mapper.map_label("cic", lbl) for lbl in raw_labels]
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
