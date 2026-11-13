"""
ml/taxonomy/labels.py
Canonical Attack Taxonomy Definitions for AdaptiveCloud.
Defines:
- 10 Canonical Families: benign, dos, ddos, brute_force, port_scan_recon,
  botnet, web_attack, infiltration, exploit_other, unknown_suspicious
- L1 Binary Label: 0 (benign) | 1 (attack)
- Label encoders, decoders, and metadata representations.
"""
from __future__ import annotations

from enum import Enum
from typing import Final


class AttackFamily(str, Enum):
    """The 10 canonical attack families mandated across all feature spaces."""
    BENIGN = "benign"
    DOS = "dos"
    DDOS = "ddos"
    BRUTE_FORCE = "brute_force"
    PORT_SCAN_RECON = "port_scan_recon"
    BOTNET = "botnet"
    WEB_ATTACK = "web_attack"
    INFILTRATION = "infiltration"
    EXPLOIT_OTHER = "exploit_other"
    UNKNOWN_SUSPICIOUS = "unknown_suspicious"


CANONICAL_FAMILIES: Final[list[str]] = [
    AttackFamily.BENIGN.value,
    AttackFamily.DOS.value,
    AttackFamily.DDOS.value,
    AttackFamily.BRUTE_FORCE.value,
    AttackFamily.PORT_SCAN_RECON.value,
    AttackFamily.BOTNET.value,
    AttackFamily.WEB_ATTACK.value,
    AttackFamily.INFILTRATION.value,
    AttackFamily.EXPLOIT_OTHER.value,
    AttackFamily.UNKNOWN_SUSPICIOUS.value,
]

FAMILY_TO_ID: Final[dict[str, int]] = {name: i for i, name in enumerate(CANONICAL_FAMILIES)}
ID_TO_FAMILY: Final[dict[int, str]] = {i: name for i, name in enumerate(CANONICAL_FAMILIES)}

# L1 Binary Mapping: 0 = benign, 1 = attack
L1_BENIGN: Final[int] = 0
L1_ATTACK: Final[int] = 1


def is_attack_family(family: str) -> bool:
    """Returns True if family is an attack or suspicious pattern."""
    return family.lower() != AttackFamily.BENIGN.value


def family_to_id(family: str) -> int:
    """Map family name to integer class ID (defaults to unknown_suspicious if unrecognised)."""
    return FAMILY_TO_ID.get(family.lower(), FAMILY_TO_ID[AttackFamily.UNKNOWN_SUSPICIOUS.value])


def id_to_family(class_id: int) -> str:
    """Map integer class ID back to canonical family name."""
    return ID_TO_FAMILY.get(class_id, AttackFamily.UNKNOWN_SUSPICIOUS.value)
