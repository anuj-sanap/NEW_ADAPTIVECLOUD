# AdaptiveCloud Threat Detection & Classification - Performance Report

**Generated:** 2026-11-11 08:30:30 UTC  
**Active Champion:** `none`  
**Evaluated Models:** 7  

## 1. Executive Summary

This report documents model evaluations conducted across isolated feature spaces 
under strict provenance tracking. Each model operates strictly within its designated 
feature space (FS-CIC, FS-UNSW, FS-KDD, FS-LIVE) without cross-space data leakage.

## 2. Model Performance Benchmarks

| Model | Feature Space | Macro F1 | Weighted F1 | Latency (ms) | Train Time (s) |
|---|---|---|---|---|---|
| `decision_tree` | FS-CIC | 0.9994 | 0.0000 | 0.000 | 0.19 |
| `random_forest` | FS-CIC | 0.9994 | 0.0000 | 0.069 | 0.72 |
| `xgboost` | FS-CIC | 0.9994 | 0.0000 | 0.003 | 2.64 |
| `svm` | FS-CIC | 0.9971 | 0.0000 | 0.040 | 0.50 |
| `isolation_forest` | FS-CIC | 0.0000 | 0.0000 | 0.026 | 0.57 |
| `threat_forecast_15m` | FS-CIC | 0.0000 | 0.0000 | 0.000 | 0.41 |
| `threat_forecast_60m` | FS-CIC | 0.0000 | 0.0000 | 0.000 | 0.34 |

## 3. Data Governance & Provenance Rules

- **Feature Space Isolation:** Datasets from different feature spaces are never merged.
- **Live Telemetry Gate:** Telemetry from live agents requires human analyst verification before entering training sets.
- **Honesty In Detections:** Models return `unknown_suspicious` when out-of-distribution, never forced into an incorrect class.
