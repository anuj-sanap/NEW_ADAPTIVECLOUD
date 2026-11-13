"""
ml/features/validator.py
Strict Schema and Feature Space Validator.
Verifies telemetry records and dataframes against their designated feature space.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Union
import pandas as pd

from ml.features.spaces import get_feature_space


class FeatureValidator:
    """
    Enforces feature schema compliance for training data and live inference records.
    """

    @staticmethod
    def validate_record(
        record: Dict[str, Any],
        feature_space: str,
        allow_missing: bool = False,
    ) -> List[str]:
        """
        Validates a single telemetry dictionary.
        Returns list of missing features. Raises ValueError if missing features exist and allow_missing is False.
        """
        space = get_feature_space(feature_space)
        missing = [f for f in space.features if f not in record]
        if missing and not allow_missing:
            raise ValueError(
                f"Validation failed for {feature_space}: missing {len(missing)} features: {missing}"
            )
        return missing

    @staticmethod
    def validate_dataframe(
        df: pd.DataFrame,
        feature_space: str,
        allow_missing: bool = False,
    ) -> List[str]:
        """
        Validates DataFrame columns against feature space definition.
        """
        space = get_feature_space(feature_space)
        present = set(df.columns)
        missing = [f for f in space.features if f not in present]
        if missing and not allow_missing:
            raise ValueError(
                f"DataFrame validation failed for {feature_space}: missing {len(missing)} features: {missing[:5]}"
            )
        return missing

    @staticmethod
    def align_dataframe(df: pd.DataFrame, feature_space: str) -> pd.DataFrame:
        """
        Reorders and extracts columns strictly corresponding to the feature space.
        Missing columns are filled with 0.0.
        """
        space = get_feature_space(feature_space)
        out = pd.DataFrame(index=df.index)
        for f in space.features:
            if f in df.columns:
                out[f] = df[f]
            else:
                out[f] = 0.0
        return out
