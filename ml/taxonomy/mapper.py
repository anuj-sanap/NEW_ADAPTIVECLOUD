"""
ml/taxonomy/mapper.py
Taxonomy Mapper loading taxonomy.yaml and mapping raw dataset labels to
the 10 canonical families, subtypes, and L1 labels.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from ml.taxonomy.labels import (
    AttackFamily,
    CANONICAL_FAMILIES,
    L1_ATTACK,
    L1_BENIGN,
    is_attack_family,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml"


class TaxonomyMapper:
    """
    Translates raw dataset labels (CIC-IDS, UNSW, NSL-KDD, Live) to
    standardized canonical families, fine-grained subtypes, and L1 binary labels.
    """

    def __init__(self, config_file: Optional[Path] = None) -> None:
        self.config_path = config_file or CONFIG_PATH
        self._mappings: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._normalized_lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.canonical_families: List[str] = list(CANONICAL_FAMILIES)
        self.load_config()

    def load_config(self) -> None:
        """Loads and parses the taxonomy configuration YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Taxonomy config not found at: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "canonical_families" in data:
            self.canonical_families = [str(x) for x in data["canonical_families"]]

        self._mappings = data.get("mappings", {})

        # Build normalized (lower-cased, whitespace-stripped) lookup tables per dataset
        self._normalized_lookup = {}
        for ds_key, ds_map in self._mappings.items():
            self._normalized_lookup[ds_key.lower()] = {}
            if isinstance(ds_map, dict):
                for raw_lbl, details in ds_map.items():
                    norm_key = self._normalize_key(str(raw_lbl))
                    self._normalized_lookup[ds_key.lower()][norm_key] = details

    @staticmethod
    def _normalize_key(k: str) -> str:
        return "".join(k.lower().split())

    def map_label(self, dataset: str, raw_label: Any) -> Tuple[str, str, int]:
        """
        Maps a raw label string from a specific dataset ('cic', 'unsw', 'kdd', 'live')
        to (family, subtype, l1).

        Honesty Rule: Unrecognized non-benign patterns are mapped to 'unknown_suspicious',
        never forced into a known class.
        """
        if raw_label is None:
            return AttackFamily.UNKNOWN_SUSPICIOUS.value, "missing_label", L1_ATTACK

        raw_str = str(raw_label).strip()
        if not raw_str:
            return AttackFamily.UNKNOWN_SUSPICIOUS.value, "empty_label", L1_ATTACK

        # Check for standard normal indicators
        norm_key = self._normalize_key(raw_str)
        if norm_key in {"benign", "normal", "0", "0.0", "white"}:
            return AttackFamily.BENIGN.value, "normal", L1_BENIGN

        ds_norm = dataset.lower().strip()
        # Aliases for dataset key
        if "cic" in ds_norm:
            lookup_key = "cic"
        elif "unsw" in ds_norm:
            lookup_key = "unsw"
        elif "kdd" in ds_norm:
            lookup_key = "kdd"
        elif "live" in ds_norm:
            lookup_key = "live"
        else:
            lookup_key = ds_norm

        ds_table = self._normalized_lookup.get(lookup_key, {})
        entry = ds_table.get(norm_key)

        if entry:
            fam = str(entry.get("family", AttackFamily.UNKNOWN_SUSPICIOUS.value))
            subtype = str(entry.get("subtype", "unknown"))
            l1 = int(entry.get("l1", L1_ATTACK))
            return fam, subtype, l1

        # Fallback for unrecognized labels: Honesty rule -> unknown_suspicious
        return AttackFamily.UNKNOWN_SUSPICIOUS.value, f"unmapped:{raw_str}", L1_ATTACK

    def get_supported_datasets(self) -> List[str]:
        """Returns the list of datasets supported by the taxonomy."""
        return list(self._mappings.keys())
