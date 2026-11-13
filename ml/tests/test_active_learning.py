"""
ml/tests/test_active_learning.py
Tests for Analyst Feedback Buffer and Human-in-the-Loop Training Gate.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from ml.learning.active_loop import AnalystFeedbackBuffer
from ml.loaders.live_loader import LiveDatasetLoader
from ml.taxonomy.labels import AttackFamily


def test_analyst_feedback_lifecycle(tmp_path: Path) -> None:
    storage = tmp_path / "feedback"
    buffer = AnalystFeedbackBuffer(storage_dir=storage)

    # 1. Enqueue suspicious live telemetry
    event_id = "ev_live_9999"
    sample_features = {"flow_duration": 120.0, "tot_fwd_pkts": 10}
    buffer.submit_telemetry_for_review(
        event_id=event_id,
        features=sample_features,
        predicted_family="unknown_suspicious",
        confidence=0.45,
    )

    assert buffer.get_pending_count() == 1
    assert buffer.get_verified_count() == 0

    # 2. Analyst rejects invalid family
    with pytest.raises(ValueError, match="Invalid attack family"):
        buffer.validate_feedback(
            event_id=event_id,
            analyst_id="analyst_alice",
            ground_truth_family="non_existent_alien_threat",
        )

    # 3. Analyst validates ground truth as port_scan_recon
    record = buffer.validate_feedback(
        event_id=event_id,
        analyst_id="analyst_alice",
        ground_truth_family=AttackFamily.PORT_SCAN_RECON.value,
        notes="Confirmed stealth scan via wireshark packet dump",
    )

    assert buffer.get_pending_count() == 0
    assert buffer.get_verified_count() == 1
    assert record["analyst_id"] == "analyst_alice"
    assert record["verified"] is True
    assert record["dataset"] == "live_cloud_events"

    # 4. Verify LiveDatasetLoader can load this verified batch
    loader = LiveDatasetLoader(raw_dir=storage, only_verified=True)
    df = loader.load_raw()
    assert len(df) == 1
    assert df.iloc[0]["family"] == AttackFamily.PORT_SCAN_RECON.value
    assert df.iloc[0]["flow_duration"] == 120.0
