"""
ml/registry/metadata.py
Schema and serialization for registered model artifacts with SHA-256 provenance.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 hexadecimal hash of a file on disk."""
    if not file_path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class ModelMetadata:
    model_name: str
    feature_space: str
    version: str
    task: str = "attack_classification"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    classes: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    macro_f1: float = 0.0
    weighted_f1: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    inference_latency_ms: float = 0.0
    training_time_sec: float = 0.0
    artifact_path: str = ""
    sha256: str = ""
    is_champion: bool = False
    evaluation_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelMetadata:
        # Filter for known fields
        valid_fields = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**clean)
