"""
ml/evaluation/benchmark.py
Comparative Model Benchmark and Candidate Ranking.
Collects evaluation results across model architectures, ranks by macro F1 and latency,
and serializes comparison.json.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.evaluation.benchmark")


class BenchmarkRunner:
    """
    Ranks evaluated models within a feature space and exports comparison summaries.
    """

    def __init__(self, models_dir: Optional[Path] = None) -> None:
        self.models_dir = models_dir or (Path(__file__).resolve().parent.parent / "models")

    def run_benchmark(self, output_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Reads all *_meta.json files in models_dir and synthesizes comparison.json.
        """
        meta_files = list(self.models_dir.glob("*_meta.json"))
        entries: List[Dict[str, Any]] = []

        for mf in meta_files:
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                # Filter for classification models
                if data.get("task") == "attack_classification" or "macro_f1" in data or "val_macro_f1" in data:
                    entries.append(data)
            except Exception as e:
                logger.warning("Could not read metadata %s: %s", mf.name, e)

        # Sort by macro F1 descending, then latency ascending
        def sort_key(item: Dict[str, Any]) -> tuple:
            f1 = item.get("macro_f1", item.get("val_macro_f1", 0.0))
            lat = item.get("inference_latency_ms", 999.0)
            return (f1, -lat)

        sorted_models = sorted(entries, key=sort_key, reverse=True)

        champion_name = sorted_models[0].get("name", sorted_models[0].get("model_name", "none")) if sorted_models else "none"

        summary: Dict[str, Any] = {
            "evaluated_models_count": len(sorted_models),
            "champion_candidate": champion_name,
            "models": sorted_models,
        }

        out_path = output_file or (self.models_dir / "comparison.json")
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        logger.info("Saved benchmark comparison to %s (Champion: %s)", out_path, champion_name)
        return summary
