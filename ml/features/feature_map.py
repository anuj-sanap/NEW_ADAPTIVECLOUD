"""
ml/features/feature_map.py
Canonical Feature Bridge between network intrusion datasets (CIC-IDS2017,
CSE-CIC-IDS2018, UNSW-NB15) and real-time Windows agent flow sniffer (flows.py).
Defines exactly 28 canonical features, dataset mapping tables, and strict validation.
"""
from __future__ import annotations

from typing import Any, Sequence
import pandas as pd


# 28 Canonical flow telemetry features shared by training datasets and agent
CANONICAL_FEATURES: tuple[str, ...] = (
    "flow_duration",      # Duration of the flow in microseconds
    "tot_fwd_pkts",       # Total packets in forward direction
    "tot_bwd_pkts",       # Total packets in backward direction
    "totlen_fwd_pkts",    # Total bytes in forward direction
    "totlen_bwd_pkts",    # Total bytes in backward direction
    "fwd_pkt_len_max",    # Max packet size forward
    "fwd_pkt_len_min",    # Min packet size forward
    "fwd_pkt_len_mean",   # Mean packet size forward
    "fwd_pkt_len_std",    # Std dev of packet size forward
    "bwd_pkt_len_max",    # Max packet size backward
    "bwd_pkt_len_min",    # Min packet size backward
    "bwd_pkt_len_mean",   # Mean packet size backward
    "bwd_pkt_len_std",    # Std dev of packet size backward
    "flow_byts_s",        # Flow throughput (bytes/second)
    "flow_pkts_s",        # Flow throughput (packets/second)
    "flow_iat_mean",      # Mean inter-arrival time (microseconds)
    "flow_iat_std",       # Std dev inter-arrival time
    "flow_iat_max",       # Max inter-arrival time
    "flow_iat_min",       # Min inter-arrival time
    "fwd_iat_mean",       # Forward packets mean IAT
    "bwd_iat_mean",       # Backward packets mean IAT
    "fin_flag_cnt",       # TCP FIN flag occurrences
    "syn_flag_cnt",       # TCP SYN flag occurrences
    "rst_flag_cnt",       # TCP RST flag occurrences
    "psh_flag_cnt",       # TCP PSH flag occurrences
    "ack_flag_cnt",       # TCP ACK flag occurrences
    "urg_flag_cnt",       # TCP URG flag occurrences
    "pkt_len_mean",       # Global average packet length across flow
)

# CIC-IDS2017 raw CSV column header mappings
CICIDS2017_MAP: dict[str, str] = {
    "Flow Duration": "flow_duration",
    "Total Fwd Packets": "tot_fwd_pkts",
    "Total Backward Packets": "tot_bwd_pkts",
    "Total Length of Fwd Packets": "totlen_fwd_pkts",
    "Total Length of Bwd Packets": "totlen_bwd_pkts",
    "Fwd Packet Length Max": "fwd_pkt_len_max",
    "Fwd Packet Length Min": "fwd_pkt_len_min",
    "Fwd Packet Length Mean": "fwd_pkt_len_mean",
    "Fwd Packet Length Std": "fwd_pkt_len_std",
    "Bwd Packet Length Max": "bwd_pkt_len_max",
    "Bwd Packet Length Min": "bwd_pkt_len_min",
    "Bwd Packet Length Mean": "bwd_pkt_len_mean",
    "Bwd Packet Length Std": "bwd_pkt_len_std",
    "Flow Bytes/s": "flow_byts_s",
    "Flow Packets/s": "flow_pkts_s",
    "Flow IAT Mean": "flow_iat_mean",
    "Flow IAT Std": "flow_iat_std",
    "Flow IAT Max": "flow_iat_max",
    "Flow IAT Min": "flow_iat_min",
    "Fwd IAT Mean": "fwd_iat_mean",
    "Bwd IAT Mean": "bwd_iat_mean",
    "FIN Flag Count": "fin_flag_cnt",
    "SYN Flag Count": "syn_flag_cnt",
    "RST Flag Count": "rst_flag_cnt",
    "PSH Flag Count": "psh_flag_cnt",
    "ACK Flag Count": "ack_flag_cnt",
    "URG Flag Count": "urg_flag_cnt",
    "Average Packet Size": "pkt_len_mean",
    "Packet Length Mean": "pkt_len_mean",
    "Label": "label",
}

# CSE-CIC-IDS2018 column header mappings
CICIDS2018_MAP: dict[str, str] = {
    "Flow Duration": "flow_duration",
    "Tot Fwd Pkts": "tot_fwd_pkts",
    "Tot Bwd Pkts": "tot_bwd_pkts",
    "TotLen Fwd Pkts": "totlen_fwd_pkts",
    "TotLen Bwd Pkts": "totlen_bwd_pkts",
    "Fwd Pkt Len Max": "fwd_pkt_len_max",
    "Fwd Pkt Len Min": "fwd_pkt_len_min",
    "Fwd Pkt Len Mean": "fwd_pkt_len_mean",
    "Fwd Pkt Len Std": "fwd_pkt_len_std",
    "Bwd Pkt Len Max": "bwd_pkt_len_max",
    "Bwd Pkt Len Min": "bwd_pkt_len_min",
    "Bwd Pkt Len Mean": "bwd_pkt_len_mean",
    "Bwd Pkt Len Std": "bwd_pkt_len_std",
    "Flow Byts/s": "flow_byts_s",
    "Flow Pkts/s": "flow_pkts_s",
    "Flow IAT Mean": "flow_iat_mean",
    "Flow IAT Std": "flow_iat_std",
    "Flow IAT Max": "flow_iat_max",
    "Flow IAT Min": "flow_iat_min",
    "Fwd IAT Mean": "fwd_iat_mean",
    "Bwd IAT Mean": "bwd_iat_mean",
    "FIN Flag Cnt": "fin_flag_cnt",
    "SYN Flag Cnt": "syn_flag_cnt",
    "RST Flag Cnt": "rst_flag_cnt",
    "PSH Flag Cnt": "psh_flag_cnt",
    "ACK Flag Cnt": "ack_flag_cnt",
    "URG Flag Cnt": "urg_flag_cnt",
    "Pkt Len Mean": "pkt_len_mean",
    "Label": "label",
}

# UNSW-NB15 column header mappings
UNSW_NB15_MAP: dict[str, str] = {
    "dur": "flow_duration",
    "spkts": "tot_fwd_pkts",
    "dpkts": "tot_bwd_pkts",
    "sbytes": "totlen_fwd_pkts",
    "dbytes": "totlen_bwd_pkts",
    "sload": "flow_byts_s",
    "sinpkt": "fwd_iat_mean",
    "dinpkt": "bwd_iat_mean",
    "attack_cat": "label",
}


def map_dataset_columns(df: pd.DataFrame, source: str = "cicids2017") -> pd.DataFrame:
    """
    Standardize raw dataset column names to canonical agent feature names.
    Strips leading/trailing whitespace from column headers before lookup.
    """
    mapping = CICIDS2017_MAP if source.lower() == "cicids2017" else CICIDS2018_MAP
    # Strip whitespace from columns
    cleaned_cols = {col: col.strip() for col in df.columns}
    df = df.rename(columns=cleaned_cols)

    # Rename according to mapping table
    rename_dict = {}
    for col in df.columns:
        if col in mapping:
            rename_dict[col] = mapping[col]

    return df.rename(columns=rename_dict)


def validate_features(data: Any, required_features: Sequence[str] = CANONICAL_FEATURES) -> None:
    """
    Validate that the incoming feature dictionary or DataFrame contains all required
    canonical features. Fails loudly with a descriptive ValueError if features are missing.
    """
    if isinstance(data, pd.DataFrame):
        present_features = set(data.columns)
    elif isinstance(data, dict):
        present_features = set(data.keys())
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        present_features = set(data[0].keys())
    else:
        raise ValueError(f"validate_features expects DataFrame or dict/list[dict], received {type(data)}")

    missing = [feat for feat in required_features if feat not in present_features]
    if missing:
        raise ValueError(
            f"Feature validation failed: missing {len(missing)} canonical flow feature(s): {missing}. "
            f"Required canonical set: {list(required_features)}"
        )
