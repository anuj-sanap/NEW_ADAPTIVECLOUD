"""
ml/tests/test_features.py
Tests for Feature Spaces, Extraction Pipelines, and Feature Space Isolation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.extractors import FeatureExtractor
from ml.features.spaces import (
    FEATURE_SPACES,
    get_feature_space,
    validate_isolation,
)
from ml.features.validator import FeatureValidator


def test_feature_spaces_definitions() -> None:
    assert "FS-CIC" in FEATURE_SPACES
    assert "FS-UNSW" in FEATURE_SPACES
    assert "FS-KDD" in FEATURE_SPACES
    assert "FS-LIVE" in FEATURE_SPACES

    cic_space = get_feature_space("FS-CIC")
    assert cic_space.feature_count == 28

    unsw_space = get_feature_space("FS-UNSW")
    assert unsw_space.feature_count == 33

    kdd_space = get_feature_space("FS-KDD")
    assert kdd_space.feature_count == 36

    live_space = get_feature_space("FS-LIVE")
    assert "cpu_percent" in live_space.features
    assert "flow_duration" in live_space.features


def test_feature_space_isolation_enforcement() -> None:
    """Critical Rule: Prevent cross-contamination between different feature spaces."""
    validate_isolation("FS-CIC", "FS-CIC")  # Valid

    with pytest.raises(ValueError, match="Feature Space Contamination Violation"):
        validate_isolation("FS-CIC", "FS-UNSW")

    with pytest.raises(ValueError, match="Feature Space Contamination Violation"):
        validate_isolation("FS-KDD", "FS-LIVE")


def test_feature_extractor_pipeline(synthetic_cic_df: pd.DataFrame) -> None:
    space = get_feature_space("FS-CIC")
    extractor = FeatureExtractor(feature_names=space.features, scaler_type="robust")

    # Inject inf and NaN to test robust sanitization
    dirty_df = synthetic_cic_df.copy()
    dirty_df.loc[0, "flow_duration"] = np.nan
    dirty_df.loc[1, "tot_fwd_pkts"] = np.inf

    X = extractor.fit_transform(dirty_df)
    assert X.shape == (len(synthetic_cic_df), 28)
    assert not np.isnan(X).any()
    assert not np.isinf(X).any()

    # Test single-record real-time inference extraction
    record = {f: 50.0 for f in space.features}
    vec = extractor.transform_dict(record)
    assert vec.shape == (1, 28)
    assert isinstance(vec, np.ndarray)


def test_feature_validator(synthetic_cic_df: pd.DataFrame) -> None:
    missing = FeatureValidator.validate_dataframe(synthetic_cic_df, "FS-CIC")
    assert len(missing) == 0

    broken = synthetic_cic_df.drop(columns=["flow_duration"])
    with pytest.raises(ValueError, match="DataFrame validation failed"):
        FeatureValidator.validate_dataframe(broken, "FS-CIC")
