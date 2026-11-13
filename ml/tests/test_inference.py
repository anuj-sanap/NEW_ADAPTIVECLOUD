"""
ml/tests/test_inference.py
Tests for Inference Engine, Honesty Rules, Cold-Start, and Heuristic Fallbacks.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from ml.features.spaces import get_feature_space
from ml.inference.engine import InferenceEngine
from ml.inference.fallback import RuleBasedFallback
from ml.taxonomy.labels import AttackFamily
from ml.training.trainer import ModelTrainer


def test_cold_start_honesty_rule(tmp_path: Path) -> None:
    """Honesty Rule: When no model is loaded, engine MUST return status 'not_available'."""
    empty_models_dir = tmp_path / "empty_models"
    empty_models_dir.mkdir(parents=True, exist_ok=True)

    engine = InferenceEngine(feature_space="FS-CIC", models_dir=empty_models_dir)
    res = engine.predict({"flow_duration": 100})
    assert res["status"] == "not_available"
    assert "No active" in res["message"]


def test_inference_engine_with_model(synthetic_cic_df: pd.DataFrame, tmp_models_dir: Path) -> None:
    # Train a model into tmp_models_dir
    trainer = ModelTrainer(feature_space="FS-CIC", output_dir=tmp_models_dir)
    trainer.train_model("random_forest", synthetic_cic_df, synthetic_cic_df, label_col="family")

    engine = InferenceEngine(feature_space="FS-CIC", models_dir=tmp_models_dir)
    assert engine.is_ready

    space = get_feature_space("FS-CIC")
    sample_flow = {f: 50.0 for f in space.features}
    res = engine.predict(sample_flow)
    assert res["status"] == "ok"
    assert "family" in res
    assert "confidence" in res
    assert "class_probabilities" in res


def test_unknown_suspicious_honesty_rule(synthetic_cic_df: pd.DataFrame, tmp_models_dir: Path) -> None:
    """Honesty Rule: Low confidence or out-of-distribution patterns are labelled unknown_suspicious."""
    trainer = ModelTrainer(feature_space="FS-CIC", output_dir=tmp_models_dir)
    trainer.train_model("random_forest", synthetic_cic_df, synthetic_cic_df, label_col="family")

    # Set extreme confidence threshold (e.g. 0.999) to force fallback
    engine = InferenceEngine(feature_space="FS-CIC", models_dir=tmp_models_dir, confidence_threshold=0.999)
    space = get_feature_space("FS-CIC")
    sample_flow = {f: 50.0 for f in space.features}
    res = engine.predict(sample_flow)
    assert res["family"] == AttackFamily.UNKNOWN_SUSPICIOUS.value
    assert res["flagged_unknown"] is True


def test_rule_based_fallback() -> None:
    # 1. Event 4625 failed logon burst
    logon_event = {
        "event_type": "windows_security_event",
        "details": {"event_id": "4625", "count": 10},
    }
    detection = RuleBasedFallback.evaluate_event(logon_event)
    assert detection is not None
    assert detection["family"] == AttackFamily.BRUTE_FORCE.value
    assert "RULE_WIN_4625_BURST" in detection["rule"]

    # 2. Mimikatz injection
    proc_event = {
        "event_type": "process_creation",
        "details": {"command_line": "powershell.exe -enc Invoke-Mimikatz"},
    }
    detection = RuleBasedFallback.evaluate_event(proc_event)
    assert detection is not None
    assert detection["family"] == AttackFamily.INFILTRATION.value

    # 3. SYN port scan
    scan_event = {
        "event_type": "network_flow",
        "syn_flag_cnt": 15,
        "ack_flag_cnt": 0,
        "flow_duration": 5000,
    }
    detection = RuleBasedFallback.evaluate_event(scan_event)
    assert detection is not None
    assert detection["family"] == AttackFamily.PORT_SCAN_RECON.value
