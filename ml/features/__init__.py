"""
ml/features package: Canonical feature bridge, feature spaces, extractors, and validators.
"""
from ml.features.extractors import FeatureExtractor
from ml.features.feature_map import (
    CANONICAL_FEATURES,
    CICIDS2017_MAP,
    CICIDS2018_MAP,
    UNSW_NB15_MAP,
    map_dataset_columns,
    validate_features,
)
from ml.features.spaces import (
    FEATURE_SPACES,
    FeatureSpace,
    get_feature_space,
    validate_isolation,
)
from ml.features.validator import FeatureValidator

__all__ = [
    "CANONICAL_FEATURES",
    "CICIDS2017_MAP",
    "CICIDS2018_MAP",
    "UNSW_NB15_MAP",
    "map_dataset_columns",
    "validate_features",
    "FeatureExtractor",
    "FeatureSpace",
    "FEATURE_SPACES",
    "get_feature_space",
    "validate_isolation",
    "FeatureValidator",
]
