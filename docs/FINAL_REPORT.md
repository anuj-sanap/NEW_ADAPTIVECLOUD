# AdaptiveCloud: AI-Based Adaptive Cloud Security and Predictive Maintenance System
**Final Engineering & Research Report**

---

## Abstract
Modern cloud infrastructures face simultaneous challenges from distributed cyber attacks and unexpected infrastructure degradation. Traditional intrusion detection systems (IDS) operate reactively, incur heavy SaaS subscription costs, and fail to provide actionable root cause analysis or continuous domain adaptation. This report presents **AdaptiveCloud**, a full-stack, zero-cost (₹0 budget) autonomous cloud security and predictive maintenance platform designed specifically for hybrid Windows Server cloud environments.

AdaptiveCloud introduces:
1. A **Universal Feature Bridge** that reconciles disparate network flow schemas from academic datasets (CIC-IDS2017) with live Windows Npcap packet capture engines.
2. A two-stage detection pipeline coupling unsupervised **Isolation Forest** anomaly scoring with multi-class **XGBoost** attack classification.
3. An automated **Forensic Root Cause Analysis (RCA)** engine generating ordered incident timelines and executable PowerShell remediation scripts.
4. Robust **Predictive Maintenance** utilizing Theil-Sen linear estimators to forecast storage exhaustion horizons days in advance.
5. A closed **Adaptive Learning Feedback Loop** employing Population Stability Index (PSI) drift tracking and Champion/Challenger promotion gates.

---

## 1. Problem Statement & Objectives
Enterprise IT infrastructures deployed on public clouds (Google Cloud, AWS) often experience:
- **Alert Fatigue & Fragmented Telemetry**: Security events, metric spikes, and network flows remain in separate silos without chronological correlation.
- **High Licensing Costs**: Commercial SIEM and APM tools (e.g. Datadog, Splunk) impose steep per-host licensing fees incompatible with academic research or lean startups.
- **Domain Gap & Concept Drift**: Machine learning models trained on static academic benchmarks fail when exposed to real-world network variations.
- **Unbudgeted Cloud Surges**: Accidental over-provisioning and unmanaged trial credits lead to unexpected cloud expenditures.

AdaptiveCloud resolves these issues through an end-to-end open architecture implemented with zero third-party software subscriptions.

---

## 2. Architecture & Implementation

```
                                 ADAPTIVECLOUD ARCHITECTURAL TOPOLOGY
                                 
   +-----------------------------------------------------------------------------------------+
   |  DATA PLANE (Google Cloud Platform)                                                     |
   |                                                                                         |
   |  +-----------------------------------------------------------------------------------+  |
   |  | Windows Server 2022 Datacenter VM (e2-medium, 50GB Disk)                          |  |
   |  |                                                                                   |  |
   |  |  +---------------------+  +---------------------+  +----------------------------+ |  |
   |  |  | WinEvent Monitor    |  | System Telemetry    |  | Network Flow Sniffer       | |  |
   |  |  | (IDs 4624/4625/4688)|  | (CPU, RAM, Disk)    |  | (Npcap 28 Canonical Feats) | |  |
   |  |  +----------+----------+  +----------+----------+  +--------------+-------------+ |  |
   |  |             |                        |                            |               |  |
   |  |             +------------------------+----------------------------+               |  |
   |  |                                      |                                            |  |
   |  |                     +----------------v-----------------+                          |  |
   |  |                     | AdaptiveCloud Windows Agent      |                          |  |
   |  |                     | (Python 3.11 Windows Service)    |                          |  |
   |  |                     +----------------+-----------------+                          |  |
   |  +--------------------------------------|--------------------------------------------+  |
   +-----------------------------------------|-----------------------------------------------+
                                             |
                                 TLS 1.3 / WireGuard Mesh
                                (Tailscale 100.64.0.0/10)
                                             |
   +-----------------------------------------v-----------------------------------------------+
   |  CONTROL PLANE (Local Workstation - Docker on WSL2)                                     |
   |                                                                                         |
   |  +-------------------+    +----------------------+    +-------------------------------+ |
   |  | Nginx SSL Gateway |===>| FastAPI Backend API  |<==>| React 18 + Vite SPA Dashboard | |
   |  | (Rate Limiter)    |    | (Async SQLAlchemy 2) |    | (Tailwind CSS, Lucide)        | |
   |  +-------------------+    +-----------+----------+    +-------------------------------+ |
   |                                       |                                                 |
   |                       +---------------+---------------+                                 |
   |                       |                               |                                 |
   |            +----------v-----------+       +-----------v-----------+                     |
   |            | PostgreSQL 16 DB     |       | ML Inference Engine   |                     |
   |            | (Relational Store)   |       | (IsolationForest/XGB) |                     |
   |            +----------------------+       +-----------------------+                     |
   +-----------------------------------------------------------------------------------------+
```

---

## 3. The Feature Bridge Methodology

A fundamental barrier in applying academic IDS datasets to live production agents is the **feature mismatch**:
- Datasets like CIC-IDS2017 define 78+ statistical features over bidirectional packet flows.
- Real-time agent packet sniffers (Npcap / Scapy) have limited memory and CPU budgets.

AdaptiveCloud bridges this divide by extracting the **28 Canonical Flow Features** supported symmetrically by both offline dataset CSVs and the real-time agent flow accumulator (`ml/features/feature_map.py`):

```python
CANONICAL_FEATURES = [
    "flow_duration", "tot_fwd_pkts", "tot_bwd_pkts", "totlen_fwd_pkts",
    "totlen_bwd_pkts", "fwd_pkt_len_max", "fwd_pkt_len_min", "fwd_pkt_len_mean",
    "fwd_pkt_len_std", "bwd_pkt_len_max", "bwd_pkt_len_min", "bwd_pkt_len_mean",
    "bwd_pkt_len_std", "flow_bytes_s", "flow_pkts_s", "flow_iat_mean",
    "flow_iat_std", "flow_iat_max", "flow_iat_min", "fwd_iat_tot",
    "bwd_iat_tot", "fwd_header_len", "bwd_header_len", "fwd_pkts_s",
    "bwd_pkts_s", "pkt_len_min", "pkt_len_max", "pkt_len_mean"
]
```

---

## 4. Model Evaluation & Benchmark Comparison

We evaluated three candidate architectures on a stratified sample of 100,000 bidirectional flow records from CIC-IDS2017:

| Model Architecture | Precision | Recall | Macro F1-Score | Inference Latency | Model Artifact Size |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **XGBoost Classifier (Selected)** | **0.994** | **0.991** | **0.992** | **1.8 ms** | **1.4 MB** |
| Random Forest (100 trees) | 0.991 | 0.988 | 0.989 | 6.2 ms | 38.2 MB |
| Logistic Regression (L2) | 0.812 | 0.795 | 0.803 | 0.4 ms | 0.2 MB |

### Attack Classification Breakdown (XGBoost Champion)
- **Benign Traffic**: Precision 0.998, Recall 0.997, F1 0.997
- **Brute Force (SSH/RDP)**: Precision 0.989, Recall 0.985, F1 0.987
- **DDoS (SYN / HTTP Flood)**: Precision 0.995, Recall 0.992, F1 0.993
- **Port Scan (TCP SYN Sweep)**: Precision 0.992, Recall 0.989, F1 0.990

---

## 5. Predictive Maintenance Formulations

Infrastructure failures frequently stem from linear exhaustion of disk partitions or sudden memory leaks. AdaptiveCloud incorporates:

### 5.1 Theil-Sen Robust Linear Estimator for Disk Fill
Given timestamp sequence $t_i$ and disk utilization percentages $y_i$, the median slope across all sample pairs $(i, j)$ is computed:

$$m = \text{median}\left(\frac{y_j - y_i}{t_j - t_i}\right) \quad \text{for } 1 \le i < j \le n$$

The estimated horizon until the $95\%$ critical exhaustion threshold is given by:

$$\Delta t_{\text{exhaustion}} = \frac{95.0 - y_{\text{current}}}{m} \quad \text{(days)}$$

This formulation is impervious to temporary disk write spikes (e.g., temporary log rotation bursts) that mislead standard ordinary least squares (OLS) regression.

---

## 6. Budget & Resource Governance Analysis

AdaptiveCloud was engineered under a strict ₹0 ($0.00) financial budget:
- **GCP Compute Engine**: Utilized Google Cloud $300 credit.
- **Worker Configuration**: 1x `e2-medium` (2 vCPU, 4GB RAM) Windows Server 2022 VM with 50 GB standard persistent disk.
- **Cost Minimization**: Automated teardown script halts the VM when idle, bounding monthly spend to < $2.00 (storage only).
- **Control Plane**: Hosted entirely on local Windows PC via WSL2 Docker Compose containers.
- **Network Routing**: Free Tailscale Personal Tier encrypted mesh (up to 100 devices at zero cost).
- **Public Domain & TLS**: DuckDNS Dynamic DNS + Let's Encrypt / SAN-enabled TLS certificates ($0.00).

---

## 7. Conclusion & Future Work
AdaptiveCloud demonstrates that robust, enterprise-grade cloud security and predictive operations do not require prohibitive subscription costs. Future enhancements will explore:
1. Extending telemetry agents to Linux and Kubernetes cluster pods.
2. Federated learning across multiple edge nodes to preserve privacy.
3. Integration with eBPF network hooks on Linux workers for kernel-level wireline packet filtering.
