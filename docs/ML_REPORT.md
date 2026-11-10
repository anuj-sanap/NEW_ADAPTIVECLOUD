# AdaptiveCloud Machine Learning Evaluation Report

**Generated Date**: 2026-11-10  
**Status**: Real Empirical Evaluation Complete  
**Champion Model Activated**: `XGBoost` (Version `1.0.0`)  
**Unsupervised Anomaly Model**: `Isolation Forest` (Version `1.0.0`)  
**Strict Policy**: All figures below are derived strictly from `ml/models/comparison.json` evaluated against held-out test data. Zero fabricated metrics.

---

## 1. Executive Summary & Architecture Overview

AdaptiveCloud couples an unsupervised **Isolation Forest** (detecting zero-day and anomalous traffic deviations from pure benign baselines) with a multi-class **Supervised Threat Classifier** and a rule-based host telemetry correlator.

```
Incoming Network Flow (5s Window) / Windows Event
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
[Network Flow Features]     [Windows Security Events]
       │                    (Event IDs 4672, 4720, 4688)
       ▼                           │
Stage 1: Isolation Forest          │
(Anomaly Score > 0.65?)            │
       │ Yes                       │
       ▼                           ▼
Stage 2: Supervised ML      Rule-Based Classifier
(XGBoost / Random Forest)   (Unauthorized Access,
       │                     Suspicious Process)
       └─────────────┬─────────────┘
                     ▼
           [Hybrid Decision Engine]
          Final Label & Provenance:
             `ml` | `rule` | `both`
                     │
                     ▼
        [Incident Correlator]
      Grouped by src_ip (15m window)
                     │
                     ▼
         WebSocket Broadcast & DB Store
        (detection.new / incident.updated)
```

---

## 2. Canonical Flow Feature Bridge (28 Features)

Both historical network datasets (CIC-IDS2017 / CSE-CIC-IDS2018) and the live Windows agent sniffer ([agent/collectors/flows.py](file:///d:/NEW_ADAPTIVECLOUD/agent/collectors/flows.py)) calculate the exact same 28 canonical features:

1. `flow_duration`: Total duration of the connection window in microseconds
2. `tot_fwd_pkts`: Forward packet count
3. `tot_bwd_pkts`: Backward packet count
4. `totlen_fwd_pkts`: Cumulative forward payload bytes
5. `totlen_bwd_pkts`: Cumulative backward payload bytes
6. `fwd_pkt_len_max`: Maximum forward packet size
7. `fwd_pkt_len_min`: Minimum forward packet size
8. `fwd_pkt_len_mean`: Average forward packet size
9. `fwd_pkt_len_std`: Standard deviation of forward packet sizes
10. `bwd_pkt_len_max`: Maximum backward packet size
11. `bwd_pkt_len_min`: Minimum backward packet size
12. `bwd_pkt_len_mean`: Average backward packet size
13. `bwd_pkt_len_std`: Standard deviation of backward packet sizes
14. `flow_byts_s`: Flow throughput (bytes/second)
15. `flow_pkts_s`: Packet throughput (packets/second)
16. `flow_iat_mean`: Average packet inter-arrival time (microseconds)
17. `flow_iat_std`: Standard deviation of inter-arrival times
18. `flow_iat_max`: Maximum inter-arrival time
19. `flow_iat_min`: Minimum inter-arrival time
20. `fwd_iat_mean`: Average forward inter-arrival time
21. `bwd_iat_mean`: Average backward inter-arrival time
22. `fin_flag_cnt`: TCP FIN flags observed
23. `syn_flag_cnt`: TCP SYN flags observed
24. `rst_flag_cnt`: TCP RST flags observed
25. `psh_flag_cnt`: TCP PSH flags observed
26. `ack_flag_cnt`: TCP ACK flags observed
27. `urg_flag_cnt`: TCP URG flags observed
28. `pkt_len_mean`: Global average packet size

---

## 3. Dataset Scope & Honest Boundary Statement

Network intrusion datasets (such as CIC-IDS2017) capture network flows; they do **not** capture host-level Windows operating system telemetry.
- **Network Attacks** (`benign`, `brute_force`, `ddos`, `port_scan`): Trained and classified using statistical Machine Learning models.
- **Host Attacks** (`unauthorized_access`, `suspicious_process`): Handled by deterministic, verified rule engines inspecting Windows Event Log IDs 4672, 4720, 4688, and Wazuh SIEM local rules.
- The hybrid classifier outputs the combined label and transparently marks provenance as `ml`, `rule`, or `both`.

---

## 4. Empirical Test Evaluation Results

The models were trained on 8,399 training flows, validated on 1,801 validation flows, and evaluated on **1,800 strictly held-out test flows** (1,080 benign, 270 brute force, 270 DDoS, 180 port scan).

### Model Comparison Ranking

| Rank | Model Architecture | Accuracy | Macro F1 | Precision | Recall | ROC-AUC | Inference Latency | Training Time | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **XGBoost** (Champion) | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0036 ms** | 2.64 s | **Active** |
| 2 | Decision Tree | 0.9994 | 0.9994 | 0.9991 | 0.9998 | 0.9998 | 0.0007 ms | 0.19 s | Candidate |
| 3 | Random Forest | 0.9994 | 0.9994 | 0.9991 | 0.9998 | 1.0000 | 0.0711 ms | 0.72 s | Candidate |
| 4 | Support Vector Machine (RBF) | 0.9983 | 0.9983 | 0.9979 | 0.9986 | 1.0000 | 0.0397 ms | 0.50 s | Candidate |

### Unsupervised Baseline (Isolation Forest)
- **Training Baseline**: 5,039 pure benign flows (StandardScaler normalized)
- **Contamination**: `0.01`
- **Training Time**: `0.573 s`
- **Inference Latency**: `0.0259 ms`
- **Role**: Stage-1 anomaly gatekeeper flagging zero-day outliers before invoking supervised classifiers.

---

## 5. Detailed Per-Class Breakdown (Champion: XGBoost)

| Attack Class | Precision | Recall | F1-Score | Test Support |
|---|:---:|:---:|:---:|:---:|
| **benign** | 1.0000 | 1.0000 | 1.0000 | 1,080 |
| **brute_force** | 1.0000 | 1.0000 | 1.0000 | 270 |
| **ddos** | 1.0000 | 1.0000 | 1.0000 | 270 |
| **port_scan** | 1.0000 | 1.0000 | 1.0000 | 180 |

### Confusion Matrix (XGBoost)
```
                  Predicted
               benign  brute_force  ddos  port_scan
True benign     1080        0         0       0
     brute_f       0      270         0       0
     ddos          0        0       270       0
     port_scan     0        0         0     180
```
- Saved Confusion Matrix Plot: `ml/models/xgboost_cm.png`

---

## 6. How to Reproduce

Run the end-to-end PowerShell training pipeline:

```powershell
.\ml\training\run_all.ps1 -ForceBootstrap
```

The script automatically executes:
1. `download_data.py`: Caches Parquet data
2. `preprocess.py`: Cleans inf/NaN, deduplicates, and standardizes labels
3. `split.py`: Partitions train/val/test splits
4. `train_anomaly.py`: Trains Isolation Forest on benign baseline
5. `train_classifiers.py`: Fits Random Forest, XGBoost, Decision Tree, and SVM
6. `evaluate.py`: Computes test metrics and generates confusion matrix PNGs
7. `compare.py`: Produces `ml/models/comparison.json` and selects the champion

