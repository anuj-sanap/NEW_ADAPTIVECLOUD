"""
backend/tests/test_ml_features.py
Unit tests for canonical feature bridge, column mapping, loud validation failures,
and real-time model inference.
"""
import pytest
import pandas as pd
from ml.features.feature_map import (
    CANONICAL_FEATURES,
    map_dataset_columns,
    validate_features,
)
from ml.inference.predictor import FlowPredictor, flow_predictor


def create_sample_flow_dict() -> dict[str, float]:
    """Helper creating a valid canonical flow dict."""
    return {feat: 10.0 for feat in CANONICAL_FEATURES}


def test_validate_features_success():
    data = create_sample_flow_dict()
    # Should complete without error
    validate_features(data)

    # Test with DataFrame
    df = pd.DataFrame([data])
    validate_features(df)


def test_validate_features_fails_loudly_on_missing_column():
    data = create_sample_flow_dict()
    # Deliberately remove required features
    del data["flow_duration"]
    del data["syn_flag_cnt"]

    with pytest.raises(ValueError) as excinfo:
        validate_features(data)

    err = str(excinfo.value)
    assert "Feature validation failed" in err
    assert "flow_duration" in err
    assert "syn_flag_cnt" in err


def test_map_dataset_columns_cicids2017():
    raw_df = pd.DataFrame({
        " Flow Duration ": [5000],
        " Total Fwd Packets ": [10],
        " Total Backward Packets ": [8],
        " Label ": ["BENIGN"],
    })
    mapped = map_dataset_columns(raw_df, source="cicids2017")
    assert "flow_duration" in mapped.columns
    assert "tot_fwd_pkts" in mapped.columns
    assert "tot_bwd_pkts" in mapped.columns
    assert "label" in mapped.columns


def test_flow_predictor_anomaly_scoring():
    flow_data = create_sample_flow_dict()
    res = flow_predictor.score_anomaly(flow_data)

    assert "status" in res
    if res["status"] == "ok":
        assert "anomaly_score" in res
        assert "is_attack" in res
        assert 0.0 <= res["anomaly_score"] <= 1.0


def test_flow_predictor_attack_classification():
    flow_data = create_sample_flow_dict()
    res = flow_predictor.classify_attack(flow_data)

    assert "status" in res
    if res["status"] == "ok":
        assert "label" in res
        assert "confidence" in res
        assert "probs" in res
        assert res["label"] in ["benign", "brute_force", "ddos", "port_scan"]


def test_predictor_honest_not_available_on_missing_models(tmp_path):
    # Predictor pointing to empty temporary directory
    empty_pred = FlowPredictor(models_dir=tmp_path)
    flow_data = create_sample_flow_dict()

    ano_res = empty_pred.score_anomaly(flow_data)
    assert ano_res == {"status": "not_available"}

    clf_res = empty_pred.classify_attack(flow_data)
    assert clf_res == {"status": "not_available"}
