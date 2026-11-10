# AdaptiveCloud Machine Learning Datasets Guide

AdaptiveCloud integrates supervised multi-class threat classification and unsupervised anomaly detection using standard network intrusion datasets coupled with host-level Windows security telemetry.

> **STRICT REPOSITORY POLICY**: Never commit raw dataset files (`*.csv`, `*.pcap`, `*.parquet`) into Git. The repository `.gitignore` ignores all contents inside `ml/data/raw/` and `ml/data/cache/`.

---

## 1. Supported Public Datasets

### A. CIC-IDS2017 (Primary Training Benchmark)
- **Source**: Canadian Institute for Cybersecurity, University of New Brunswick
- **Official URL**: [UNB CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html)
- **Description**: Captured over 5 days (Monday to Friday) covering normal traffic and common modern attacks (FTP-Patator, SSH-Patator, DoS/DDoS, PortScan).
- **Download**: Download `GeneratedLabelledFlows.zip` or individual day CSVs into `ml/data/raw/cicids2017/`.

### B. CSE-CIC-IDS2018 (Generalization & Cross-Evaluation)
- **Source**: Communications Security Establishment (CSE) & CIC (AWS Open Data)
- **Official URL**: [UNB CSE-CIC-IDS2018](https://www.unb.ca/cic/datasets/ids-2018.html)
- **S3 Bucket**: `s3://cse-cic-ids2018/ProcessedTrafficDataStore/`
- **Description**: Enterprise-scale AWS environment captures across 10 days.

### C. UNSW-NB15
- **Source**: Cyber Range Lab of the Australian Centre for Cyber Security (ACCS)
- **Official URL**: [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- **Description**: Hybrid real modern normal activities and synthetic contemporary attack behaviors.

---

## 2. Attack Label Alignment & Honest Dataset Scope

AdaptiveCloud operates on 6 canonical attack labels:
1. `benign`: Normal background and operational traffic.
2. `brute_force`: Repeated credential guessing (SSH-Patator, FTP-Patator).
3. `ddos`: High-rate volumetric denial-of-service floods.
4. `port_scan`: Horizontal and vertical port sweeps and discovery.
5. `unauthorized_access`: Privilege escalation (Event 4672), rogue user account creation (Event 4720).
6. `suspicious_process`: Malicious execution from `%TEMP%`, `%APPDATA%`, or encoded PowerShell (Event 4688).

### Important Domain Fact
Network flow datasets (CIC-IDS2017, CSE-CIC-IDS2018) capture IP-level packet timings and packet sizes; they **do not** contain Windows security event logs or process execution parent-child trees.
Therefore:
- **Network Attacks** (`benign`, `brute_force`, `ddos`, `port_scan`) are classified using trained **Machine Learning models** (Random Forest, XGBoost, Isolation Forest).
- **Host Attacks** (`unauthorized_access`, `suspicious_process`) are classified using **Rule-Based Hybrid Classifiers** grounded directly in verified Windows Event Log audits (Events 4672, 4720, 4688) and Wazuh SIEM rules.
- The inference engine merges ML predictions and rule findings into a unified result with provenance tag: `ml`, `rule`, or `both`.

---

## 3. Automated Subsampling & Parquet Caching

To guarantee smooth execution on laptops (8–16 GB RAM) and Google Colab free tier (12 GB RAM):
- `ml/training/download_data.py` takes an optional `--sample-ratio 0.05` to `0.10` (5% to 10% stratified sampling).
- Processed data is cached in `ml/data/cache/*.parquet` for fast 100x faster I/O compared to raw CSVs.
- If external connectivity is unavailable or network datasets are not yet downloaded, `download_data.py --bootstrap-sample` generates a realistic, statistically calibrated stratified benchmark dataset directly matching the exact 28 CIC-IDS2017 flow feature schema.

