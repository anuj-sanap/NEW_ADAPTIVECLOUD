"""
ml/features/spaces.py
Feature Spaces Definition and Isolation Enforcer.
Defines: FS-CIC, FS-UNSW, FS-KDD, FS-LIVE.
CRITICAL DESIGN RULE: Each dataset strictly belongs to ONE feature space.
Datasets from different feature spaces MUST NEVER be concatenated or merged.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "feature_spaces.yaml"


@dataclass(frozen=True)
class FeatureSpace:
    name: str
    description: str
    dataset_compatibility: List[str]
    features: List[str]

    @property
    def feature_count(self) -> int:
        return len(self.features)


def load_feature_spaces(config_file: Optional[Path] = None) -> Dict[str, FeatureSpace]:
    """Loads feature space definitions from configuration YAML."""
    path = config_file or CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"feature_spaces.yaml not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    spaces: Dict[str, FeatureSpace] = {}
    for key, spec in data.get("feature_spaces", {}).items():
        spaces[key] = FeatureSpace(
            name=spec.get("name", key),
            description=spec.get("description", ""),
            dataset_compatibility=list(spec.get("dataset_compatibility", [])),
            features=list(spec.get("features", [])),
        )
    return spaces


FEATURE_SPACES: Dict[str, FeatureSpace] = load_feature_spaces()


def get_feature_space(name: str) -> FeatureSpace:
    """Retrieve FeatureSpace by name (e.g. 'FS-CIC')."""
    key = name.upper().strip()
    if key not in FEATURE_SPACES:
        raise ValueError(
            f"Unknown feature space: {name}. Available feature spaces: {list(FEATURE_SPACES.keys())}"
        )
    return FEATURE_SPACES[key]


def validate_isolation(space_a: str, space_b: str) -> None:
    """
    Enforces feature space isolation.
    Raises ValueError if two operations attempt to merge different feature spaces.
    """
    if space_a.upper().strip() != space_b.upper().strip():
        raise ValueError(
            f"Feature Space Contamination Violation! Cannot combine {space_a} with {space_b}. "
            f"Each dataset belongs to an isolated feature space and cannot be concatenated."
        )
