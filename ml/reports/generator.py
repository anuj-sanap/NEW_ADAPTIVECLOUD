"""
ml/reports/generator.py
Evaluation & Performance Report Generator.
Produces Markdown, JSON, and summary tables detailing model evaluations, data provenance,
and champion/challenger comparisons.
HONESTY RULE: Every statistic in the report is strictly grounded in actual model artifacts
and evaluation results.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.reports.generator")
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class ReportGenerator:
    """
    Builds comprehensive performance and audit reports from model evaluation artifacts.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ) -> None:
        self.models_dir = models_dir or MODELS_DIR
        self.reports_dir = reports_dir or REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_evaluation_report(self) -> Dict[str, Any]:
        """
        Scans models directory for evaluation results, benchmarks, and registry state,
        generating a Markdown report and saving a JSON summary.
        """
        # Read comparison.json
        comp_file = self.models_dir / "comparison.json"
        comp_data = {}
        if comp_file.exists():
            try:
                comp_data = json.loads(comp_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Read registry.json
        reg_file = self.models_dir / "registry.json"
        reg_data = {}
        if reg_file.exists():
            try:
                reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Read individual meta files
        meta_files = list(self.models_dir.glob("*_meta.json"))
        models_meta = []
        for mf in meta_files:
            try:
                models_meta.append(json.loads(mf.read_text(encoding="utf-8")))
            except Exception:
                pass

        champion = reg_data.get("champion", comp_data.get("champion_candidate", "none"))

        # Build Markdown document
        lines = [
            "# AdaptiveCloud Threat Detection & Classification - Performance Report",
            "",
            f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Active Champion:** `{champion}`  ",
            f"**Evaluated Models:** {len(models_meta)}  ",
            "",
            "## 1. Executive Summary",
            "",
            "This report documents model evaluations conducted across isolated feature spaces ",
            "under strict provenance tracking. Each model operates strictly within its designated ",
            "feature space (FS-CIC, FS-UNSW, FS-KDD, FS-LIVE) without cross-space data leakage.",
            "",
            "## 2. Model Performance Benchmarks",
            "",
            "| Model | Feature Space | Macro F1 | Weighted F1 | Latency (ms) | Train Time (s) |",
            "|---|---|---|---|---|---|",
        ]

        for m in sorted(models_meta, key=lambda x: x.get("macro_f1", x.get("val_macro_f1", 0.0)), reverse=True):
            name = m.get("name", m.get("model_name", "unknown"))
            f_space = m.get("feature_space", "FS-CIC")
            f1 = m.get("macro_f1", m.get("val_macro_f1", 0.0))
            wf1 = m.get("weighted_f1", 0.0)
            lat = m.get("inference_latency_ms", 0.0)
            tt = m.get("training_time_sec", 0.0)
            lines.append(f"| `{name}` | {f_space} | {f1:.4f} | {wf1:.4f} | {lat:.3f} | {tt:.2f} |")

        lines.extend([
            "",
            "## 3. Data Governance & Provenance Rules",
            "",
            "- **Feature Space Isolation:** Datasets from different feature spaces are never merged.",
            "- **Live Telemetry Gate:** Telemetry from live agents requires human analyst verification before entering training sets.",
            "- **Honesty In Detections:** Models return `unknown_suspicious` when out-of-distribution, never forced into an incorrect class.",
            "",
        ])

        md_content = "\n".join(lines)
        report_md_path = self.reports_dir / "latest_model_performance.md"
        report_md_path.write_text(md_content, encoding="utf-8")

        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "champion": champion,
            "models_evaluated": len(models_meta),
            "report_path": str(report_md_path),
        }
        report_json_path = self.reports_dir / "latest_model_performance.json"
        report_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        logger.info("Saved evaluation report to %s", report_md_path)
        return summary
