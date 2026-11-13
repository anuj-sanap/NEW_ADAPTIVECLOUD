"""
ml/learning/active_loop.py
Human-in-the-Loop Analyst Feedback Buffer and Promotion Gate.
CRITICAL DESIGN RULE: Live cloud events are NEVER stored as dataset rows or
used for training until explicitly validated and signed off by a human security analyst.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from ml.features.spaces import get_feature_space
from ml.taxonomy.labels import AttackFamily

logger = logging.getLogger("ml.learning.active_loop")
FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "live_feedback"


class AnalystFeedbackBuffer:
    """
    Manages unverified live events and human analyst validation workflow.
    """

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or FEEDBACK_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file = self.storage_dir / "pending_review.json"
        self.verified_file = self.storage_dir / "verified_training_pool.parquet"
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._load_pending()

    def _load_pending(self) -> None:
        if self.pending_file.exists():
            try:
                self._pending = json.loads(self.pending_file.read_text(encoding="utf-8"))
            except Exception:
                self._pending = {}
        else:
            self._pending = {}

    def _save_pending(self) -> None:
        self.pending_file.write_text(json.dumps(self._pending, indent=2), encoding="utf-8")

    def submit_telemetry_for_review(
        self,
        event_id: str,
        features: Dict[str, Any],
        predicted_family: str,
        confidence: float,
        reason: str = "low_confidence_or_outlier",
    ) -> None:
        """
        Enqueues an unverified live event for analyst review.
        """
        self._pending[event_id] = {
            "event_id": event_id,
            "features": features,
            "predicted_family": predicted_family,
            "confidence": round(confidence, 4),
            "reason": reason,
            "submitted_at": datetime.now(UTC).isoformat(),
            "verified": False,
        }
        self._save_pending()
        logger.info("Enqueued event %s for analyst review (Reason: %s)", event_id, reason)

    def validate_feedback(
        self,
        event_id: str,
        analyst_id: str,
        ground_truth_family: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Analyst validates ground-truth. Promotes the item from unverified queue to verified pool.
        """
        if event_id not in self._pending:
            raise KeyError(f"Event ID {event_id} not found in pending review queue.")

        # Validate ground_truth_family before removing from queue
        valid_families = [f.value for f in AttackFamily]
        if ground_truth_family not in valid_families:
            raise ValueError(f"Invalid attack family: {ground_truth_family}. Must be one of {valid_families}")

        entry = self._pending.pop(event_id)
        self._save_pending()

        verified_record = {
            "row_id": event_id,
            "event_id": event_id,
            "analyst_id": analyst_id,
            "ground_truth": ground_truth_family,
            "original_label": ground_truth_family,
            "family": ground_truth_family,
            "subtype": f"live_validated_{ground_truth_family}",
            "l1": 0 if ground_truth_family == AttackFamily.BENIGN.value else 1,
            "dataset": "live_cloud_events",
            "source_file": "verified_training_pool.parquet",
            "verified": True,
            "notes": notes,
            "validated_at": datetime.now(UTC).isoformat(),
            "split": "train",
        }
        # Merge telemetry features
        features = entry.get("features", {})
        verified_record.update(features)

        # Append to verified pool Parquet
        new_row = pd.DataFrame([verified_record])
        if self.verified_file.exists():
            existing = pd.read_parquet(self.verified_file, engine="pyarrow")
            updated = pd.concat([existing, new_row], ignore_index=True)
        else:
            updated = new_row

        updated.to_parquet(self.verified_file, index=False, engine="pyarrow")
        logger.info("Analyst %s validated event %s as '%s'.", analyst_id, event_id, ground_truth_family)
        return verified_record

    def get_pending_count(self) -> int:
        return len(self._pending)

    def get_verified_count(self) -> int:
        if not self.verified_file.exists():
            return 0
        df = pd.read_parquet(self.verified_file, engine="pyarrow")
        return len(df)
