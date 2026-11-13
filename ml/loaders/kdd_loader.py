"""
ml/loaders/kdd_loader.py
Dataset Loader for FS-KDD (NSL-KDD & KDDCup99).
Enforces feature space isolation for NSL-KDD, extracts numerical connection features,
attaches full provenance, and translates raw attack types into canonical families.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from ml.loaders.base import BaseDatasetLoader, PROVENANCE_COLUMNS
from ml.taxonomy.mapper import TaxonomyMapper

logger = logging.getLogger("ml.loaders.kdd")

KDD_ALL_COLUMNS: List[str] = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login",
    "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label", "difficulty"
]


class KDDDatasetLoader(BaseDatasetLoader):
    """
    Loader for NSL-KDD dataset strictly adhering to FS-KDD.
    """

    def __init__(
        self,
        dataset_name: str = "nsl-kdd",
        raw_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        mapper: Optional[TaxonomyMapper] = None,
    ) -> None:
        super().__init__(
            dataset_name=dataset_name,
            feature_space="FS-KDD",
            raw_dir=raw_dir,
            cache_dir=cache_dir,
            mapper=mapper,
        )

    def load_raw(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Parses raw NSL-KDD files into FS-KDD representation.
        Handles both standard headerless NSL-KDD data files (.txt, .csv) and headered files.
        """
        if not self.raw_dir.exists():
            self.raw_dir.mkdir(parents=True, exist_ok=True)

        candidate_files = sorted(list(self.raw_dir.glob("*.csv")) + list(self.raw_dir.glob("*.txt")))
        if not candidate_files:
            logger.warning("No CSV/TXT files found in %s for %s", self.raw_dir, self.dataset_name)
            return pd.DataFrame(columns=self.expected_features + PROVENANCE_COLUMNS)

        records: List[pd.DataFrame] = []
        rows_so_far = 0

        for file_path in candidate_files:
            if max_rows and rows_so_far >= max_rows:
                break

            logger.info("Reading KDD file %s...", file_path.name)
            # Peek first row to detect header
            sample_line = pd.read_csv(file_path, nrows=1, header=None)
            has_header = False
            first_val = str(sample_line.iloc[0, 0]).strip().lower()
            if first_val in ("duration", "protocol_type", "src_bytes"):
                has_header = True

            chunk_size = 50_000
            for chunk in pd.read_csv(
                file_path,
                header=0 if has_header else None,
                names=None if has_header else KDD_ALL_COLUMNS[: len(sample_line.columns)],
                chunksize=chunk_size,
                low_memory=False,
                encoding="utf-8",
                on_bad_lines="skip",
            ):
                chunk.columns = [str(c).strip().lower() for c in chunk.columns]

                # Identify label column
                raw_labels = chunk["label"].astype(str).str.strip() if "label" in chunk.columns else pd.Series(["normal"] * len(chunk))
                # Remove trailing dots often present in KDDcup (e.g., 'smurf.')
                raw_labels = raw_labels.str.rstrip(".")

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

                mapped = [self.mapper.map_label("kdd", lbl) for lbl in raw_labels]
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
