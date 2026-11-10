"""
ml/training/register_model.py
Registers trained model artifacts and evaluation benchmarks into
the PostgreSQL database (ml_models and model_evaluations tables).
Marks champion classifier and isolation forest as active deployments.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Backend app imports
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.ml import MLModel, ModelEvaluation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("register_model")


async def register_models_in_db(models_dir: Path, comparison_file: Path) -> None:
    if not comparison_file.exists():
        raise FileNotFoundError(f"{comparison_file} not found. Run compare.py first.")

    comp_data = json.loads(comparison_file.read_text(encoding="utf-8"))
    best_classifier = comp_data.get("best_model")
    models = comp_data.get("models", {})

    async with AsyncSessionLocal() as db:
        # 1. Register Isolation Forest Anomaly Detector
        iso_meta_file = models_dir / "isolation_forest_meta.json"
        if iso_meta_file.exists():
            iso_meta = json.loads(iso_meta_file.read_text(encoding="utf-8"))
            stmt = select(MLModel).where(MLModel.name == "isolation_forest", MLModel.version == "1.0.0")
            res = await db.execute(stmt)
            iso_record = res.scalar_one_or_none()

            metrics = {
                "training_time_sec": iso_meta.get("training_time_sec", 0.0),
                "inference_latency_ms": iso_meta.get("inference_latency_ms", 0.0),
                "contamination": iso_meta.get("contamination", 0.01),
                "train_samples": iso_meta.get("train_samples", 0),
            }

            if not iso_record:
                iso_record = MLModel(
                    name="isolation_forest",
                    task="anomaly",
                    version="1.0.0",
                    metrics=metrics,
                    artifact_path=iso_meta.get("artifact_path", "ml/models/isolation_forest.joblib"),
                    status="active",
                )
                db.add(iso_record)
                logger.info("Registered active Isolation Forest anomaly detector")
            else:
                iso_record.metrics = metrics
                iso_record.status = "active"

        # 2. Register Supervised Classifiers
        for name, mdata in models.items():
            version = mdata.get("version", "1.0.0")
            stmt = select(MLModel).where(MLModel.name == name, MLModel.version == version)
            res = await db.execute(stmt)
            model_record = res.scalar_one_or_none()

            metrics = {
                "accuracy": mdata.get("accuracy", 0.0),
                "f1_macro": mdata.get("f1_macro", 0.0),
                "precision_macro": mdata.get("precision_macro", 0.0),
                "recall_macro": mdata.get("recall_macro", 0.0),
                "roc_auc": mdata.get("roc_auc", 0.0),
                "inference_latency_ms": mdata.get("inference_latency_ms", 0.0),
                "training_time_sec": mdata.get("training_time_sec", 0.0),
            }
            status = "active" if name == best_classifier else "candidate"

            artifact_rel = f"ml/models/{name}.joblib"

            if not model_record:
                model_record = MLModel(
                    name=name,
                    task="attack_classification",
                    version=version,
                    metrics=metrics,
                    artifact_path=artifact_rel,
                    status=status,
                )
                db.add(model_record)
                await db.flush()
                logger.info("Registered %s classifier (status: %s)", name, status)
            else:
                model_record.metrics = metrics
                model_record.status = status
                await db.flush()

            # Record formal benchmark evaluation
            eval_record = ModelEvaluation(
                model_id=model_record.id,
                dataset_name="CIC-IDS2017-Test-Holdout",
                metrics=mdata,
                notes=f"Test holdout evaluation: Accuracy={metrics['accuracy']}, Macro-F1={metrics['f1_macro']}",
            )
            db.add(eval_record)

        await db.commit()
        logger.info("Database registration completed successfully. Champion: %s marked active.", best_classifier)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register ML models into database")
    parser.add_argument("--models-dir", type=str, default="ml/models")
    parser.add_argument("--comparison", type=str, default="ml/models/comparison.json")
    args = parser.parse_args()

    asyncio.run(register_models_in_db(REPO_ROOT / args.models_dir, REPO_ROOT / args.comparison))


if __name__ == "__main__":
    main()

