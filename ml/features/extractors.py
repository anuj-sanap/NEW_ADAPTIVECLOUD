"""
ml/features/extractors.py
Feature Extractor and Preprocessing Pipeline.
Performs median imputation, numerical sanitization, quantile clipping,
and feature scaling (RobustScaler or StandardScaler) per feature space.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler

logger = logging.getLogger("ml.features.extractors")


class FeatureExtractor:
    """
    Stateful preprocessor for tabular feature spaces.
    Stores medians for imputation, clip limits, and a fitted scaler.
    """

    def __init__(
        self,
        feature_names: List[str],
        scaler_type: str = "robust",
        clip_quantiles: Optional[tuple[float, float]] = (0.001, 0.999),
    ) -> None:
        self.feature_names = list(feature_names)
        self.scaler_type = scaler_type.lower()
        self.clip_quantiles = clip_quantiles

        self.medians_: Dict[str, float] = {}
        self.clip_lower_: Dict[str, float] = {}
        self.clip_upper_: Dict[str, float] = {}
        self.scaler_: Union[RobustScaler, StandardScaler] = (
            RobustScaler() if self.scaler_type == "robust" else StandardScaler()
        )
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame) -> FeatureExtractor:
        """Computes imputation values, clipping boundaries, and fits scaler."""
        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            raise ValueError(f"Cannot fit FeatureExtractor: missing features: {missing[:5]}")

        X = df[self.feature_names].copy()

        # Sanitize infs
        X = X.replace([np.inf, -np.inf], np.nan)

        # Calculate medians for imputation
        self.medians_ = {}
        for feat in self.feature_names:
            series = pd.to_numeric(X[feat], errors="coerce")
            med = float(series.median())
            self.medians_[feat] = 0.0 if np.isnan(med) else med
            X[feat] = series.fillna(self.medians_[feat])

        # Calculate clip boundaries if requested
        if self.clip_quantiles:
            q_low, q_high = self.clip_quantiles
            for feat in self.feature_names:
                series = X[feat]
                low_val = float(series.quantile(q_low))
                high_val = float(series.quantile(q_high))
                self.clip_lower_[feat] = low_val
                self.clip_upper_[feat] = high_val
                X[feat] = series.clip(lower=low_val, upper=high_val)

        # Fit scaler
        self.scaler_.fit(X.values)
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms input DataFrame using fitted parameters."""
        if not self.is_fitted:
            raise RuntimeError("FeatureExtractor must be fitted before calling transform().")

        X = pd.DataFrame(index=df.index)
        for feat in self.feature_names:
            if feat in df.columns:
                series = pd.to_numeric(df[feat], errors="coerce").replace([np.inf, -np.inf], np.nan)
                X[feat] = series.fillna(self.medians_.get(feat, 0.0))
            else:
                X[feat] = self.medians_.get(feat, 0.0)

            if self.clip_quantiles and feat in self.clip_lower_:
                X[feat] = X[feat].clip(
                    lower=self.clip_lower_[feat],
                    upper=self.clip_upper_[feat],
                )

        return self.scaler_.transform(X.values).astype(np.float32)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        return self.fit(df).transform(df)

    def transform_dict(self, record: Dict[str, Any]) -> np.ndarray:
        """Transforms a single feature dictionary for real-time inference."""
        if not self.is_fitted:
            raise RuntimeError("FeatureExtractor must be fitted before calling transform_dict().")

        vec = np.zeros((1, len(self.feature_names)), dtype=np.float32)
        for i, feat in enumerate(self.feature_names):
            val = record.get(feat)
            try:
                num = float(val) if val is not None else self.medians_.get(feat, 0.0)
                if np.isnan(num) or np.isinf(num):
                    num = self.medians_.get(feat, 0.0)
            except (ValueError, TypeError):
                num = self.medians_.get(feat, 0.0)

            if self.clip_quantiles and feat in self.clip_lower_:
                num = max(self.clip_lower_[feat], min(self.clip_upper_[feat], num))

            vec[0, i] = num

        return self.scaler_.transform(vec).astype(np.float32)

    def save(self, path: Path) -> Path:
        """Serializes extractor to joblib file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path) -> FeatureExtractor:
        """Loads serialized FeatureExtractor from joblib."""
        if not path.exists():
            raise FileNotFoundError(f"FeatureExtractor artifact not found at {path}")
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is not FeatureExtractor: {type(obj)}")
        return obj
