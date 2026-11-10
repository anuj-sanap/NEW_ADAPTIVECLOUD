"""
ml/training/compare.py
Cross-architecture model comparison and champion selection.
Reads evaluation records, compiles comparative metrics, ranks models by Macro F1,
and produces ml/models/comparison.json along with an ASCII summary table.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compare")


def compare_models(models_dir: Path, output_file: Path) -> dict[str, Any]:
    eval_files = list(models_dir.glob("*_evaluation.json"))
    if not eval_files:
        raise FileNotFoundError(f"No *_evaluation.json files found in {models_dir}. Run evaluate.py first.")

    models_data: dict[str, dict[str, Any]] = {}

    for ef in eval_files:
        data = json.loads(ef.read_text(encoding="utf-8"))
        name = data["name"]

        # Also pull training time from *_meta.json if present
        meta_file = models_dir / f"{name}_meta.json"
        train_time = 0.0
        if meta_file.exists():
            meta_json = json.loads(meta_file.read_text(encoding="utf-8"))
            train_time = meta_json.get("training_time_sec", 0.0)

        data["training_time_sec"] = train_time
        models_data[name] = data

    # Rank by Macro F1 desc, then latency asc
    ranked = sorted(
        models_data.keys(),
        key=lambda k: (models_data[k].get("f1_macro", 0.0), -models_data[k].get("inference_latency_ms", 999.0)),
        reverse=True,
    )
    champion = ranked[0]

    comparison_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "selection_metric": "f1_macro",
        "best_model": champion,
        "ranking": ranked,
        "models": models_data,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(comparison_payload, indent=2), encoding="utf-8")
    logger.info("Saved model comparison to %s (Champion: %s)", output_file, champion)

    # Print ASCII metrics table
    header = f"{'Model':<16} | {'Accuracy':<10} | {'Macro F1':<10} | {'Precision':<10} | {'Recall':<10} | {'ROC-AUC':<10} | {'Latency (ms)':<12} | {'Train (s)':<10}"
    divider = "-" * len(header)
    print("\n" + "=" * len(header))
    print("                  ADAPTIVECLOUD ML CLASSIFIER COMPARISON")
    print("=" * len(header))
    print(header)
    print(divider)
    for name in ranked:
        m = models_data[name]
        is_best = " *" if name == champion else ""
        print(
            f"{name + is_best:<16} | "
            f"{m.get('accuracy', 0.0):<10.4f} | "
            f"{m.get('f1_macro', 0.0):<10.4f} | "
            f"{m.get('precision_macro', 0.0):<10.4f} | "
            f"{m.get('recall_macro', 0.0):<10.4f} | "
            f"{m.get('roc_auc', 0.0):<10.4f} | "
            f"{m.get('inference_latency_ms', 0.0):<12.4f} | "
            f"{m.get('training_time_sec', 0.0):<10.2f}"
        )
    print(divider)
    print(f"* Champion Model Selected: {champion.upper()} (highest Macro F1 on held-out test data)\n")

    return comparison_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare evaluated models and select champion")
    parser.add_argument("--models-dir", type=str, default="ml/models")
    parser.add_argument("--output", type=str, default="ml/models/comparison.json")
    args = parser.parse_args()

    compare_models(REPO_ROOT / args.models_dir, REPO_ROOT / args.output)


if __name__ == "__main__":
    main()

