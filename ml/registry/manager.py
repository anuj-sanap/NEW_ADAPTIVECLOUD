"""
ml/registry/manager.py
Model Registry and Champion / Challenger Promotion Gate.
Enforces strict performance requirements before promoting a challenger model to production champion.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ml.registry.metadata import ModelMetadata, compute_file_sha256

logger = logging.getLogger("ml.registry.manager")
DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parent.parent / "models"


class ModelRegistry:
    """
    Central repository of versioned, evaluated models with champion/challenger tracking.
    """

    def __init__(self, registry_dir: Optional[Path] = None) -> None:
        self.registry_dir = registry_dir or DEFAULT_REGISTRY_DIR
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.registry_dir / "registry.json"
        self._registry: Dict[str, Dict[str, Any]] = {}
        self.load_manifest()

    def load_manifest(self) -> None:
        """Loads registry manifest from disk if it exists."""
        if self.manifest_path.exists():
            try:
                self._registry = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed reading registry manifest %s: %s", self.manifest_path, e)
                self._registry = {}
        else:
            self._registry = {"champion": None, "models": {}}

    def save_manifest(self) -> None:
        """Serializes registry manifest to disk."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(self._registry, indent=2), encoding="utf-8")

    def register(self, meta: ModelMetadata, artifact_path: Path) -> ModelMetadata:
        """
        Registers a trained model, computes its SHA-256 hash, and saves to manifest.
        """
        if artifact_path.exists():
            meta.sha256 = compute_file_sha256(artifact_path)
            meta.artifact_path = str(artifact_path)

        model_key = f"{meta.model_name}:{meta.version}"
        if "models" not in self._registry:
            self._registry["models"] = {}

        self._registry["models"][model_key] = meta.to_dict()

        # If no champion exists yet, auto-promote first registered model
        if self._registry.get("champion") is None:
            meta.is_champion = True
            self._registry["champion"] = model_key
            self._registry["models"][model_key]["is_champion"] = True
            logger.info("Auto-promoted initial model %s as Champion.", model_key)

        self.save_manifest()
        return meta

    def promote_to_champion(self, model_key: str, min_f1_gain: float = 0.005) -> bool:
        """
        Promotes a registered model to Champion if its macro F1 strictly improves
        upon the incumbent champion by at least min_f1_gain.
        """
        models = self._registry.get("models", {})
        if model_key not in models:
            raise KeyError(f"Model {model_key} not found in registry.")

        challenger_data = models[model_key]
        challenger_f1 = challenger_data.get("macro_f1", 0.0)

        current_champ_key = self._registry.get("champion")
        if current_champ_key and current_champ_key in models:
            current_f1 = models[current_champ_key].get("macro_f1", 0.0)
            if challenger_f1 < (current_f1 + min_f1_gain):
                logger.warning(
                    "Promotion rejected: Challenger %s macro F1 (%.4f) did not exceed "
                    "incumbent %s macro F1 (%.4f) by margin (%.4f).",
                    model_key,
                    challenger_f1,
                    current_champ_key,
                    current_f1,
                    min_f1_gain,
                )
                return False
            # Demote incumbent
            models[current_champ_key]["is_champion"] = False

        # Promote challenger
        challenger_data["is_champion"] = True
        self._registry["champion"] = model_key
        self.save_manifest()
        logger.info("Successfully promoted %s to Champion!", model_key)
        return True

    def get_champion(self) -> Optional[ModelMetadata]:
        """Returns the current champion metadata or None."""
        champ_key = self._registry.get("champion")
        if not champ_key:
            return None
        models = self._registry.get("models", {})
        data = models.get(champ_key)
        return ModelMetadata.from_dict(data) if data else None

    def list_models(self) -> List[ModelMetadata]:
        """Lists all registered models."""
        models = self._registry.get("models", {})
        return [ModelMetadata.from_dict(v) for v in models.values()]
