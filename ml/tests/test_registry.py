"""
ml/tests/test_registry.py
Tests for Model Registry, SHA-256 Provenance, and Champion/Challenger Promotion Gate.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from ml.registry.manager import ModelRegistry
from ml.registry.metadata import ModelMetadata, compute_file_sha256


def test_sha256_computation(tmp_path: Path) -> None:
    test_file = tmp_path / "dummy_artifact.bin"
    test_file.write_bytes(b"ADAPTIVE_CLOUD_MODEL_BYTES_TEST")
    sha = compute_file_sha256(test_file)
    assert len(sha) == 64
    assert isinstance(sha, str)


def test_model_registry_lifecycle(tmp_path: Path) -> None:
    reg_dir = tmp_path / "registry"
    registry = ModelRegistry(registry_dir=reg_dir)

    # Create dummy artifact 1
    art1 = reg_dir / "rf_v1.joblib"
    art1.write_bytes(b"rf_v1")
    meta1 = ModelMetadata(
        model_name="rf",
        feature_space="FS-CIC",
        version="1.0.0",
        macro_f1=0.880,
    )
    reg_meta1 = registry.register(meta1, art1)
    # First model is auto-promoted to champion
    assert reg_meta1.is_champion is True
    assert registry.get_champion().model_name == "rf"

    # Register challenger 2 with lower performance (0.870)
    art2 = reg_dir / "xgb_v1.joblib"
    art2.write_bytes(b"xgb_v1")
    meta2 = ModelMetadata(
        model_name="xgb",
        feature_space="FS-CIC",
        version="1.0.0",
        macro_f1=0.870,
    )
    registry.register(meta2, art2)

    # Challenger attempt to promote should fail (0.870 < 0.880 + 0.005)
    promoted = registry.promote_to_champion("xgb:1.0.0", min_f1_gain=0.005)
    assert promoted is False
    assert registry.get_champion().model_name == "rf"

    # Register superior challenger 3 (0.910)
    art3 = reg_dir / "lgbm_v1.joblib"
    art3.write_bytes(b"lgbm_v1")
    meta3 = ModelMetadata(
        model_name="lgbm",
        feature_space="FS-CIC",
        version="1.0.0",
        macro_f1=0.910,
    )
    registry.register(meta3, art3)

    # Challenger attempt should succeed
    promoted = registry.promote_to_champion("lgbm:1.0.0", min_f1_gain=0.005)
    assert promoted is True
    assert registry.get_champion().model_name == "lgbm"
