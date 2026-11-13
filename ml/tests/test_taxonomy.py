"""
ml/tests/test_taxonomy.py
Unit tests for Attack Taxonomy and TaxonomyMapper.
"""
from __future__ import annotations

import pytest
from ml.taxonomy.labels import (
    AttackFamily,
    CANONICAL_FAMILIES,
    FAMILY_TO_ID,
    ID_TO_FAMILY,
    family_to_id,
    id_to_family,
    is_attack_family,
)
from ml.taxonomy.mapper import TaxonomyMapper


def test_canonical_families_count() -> None:
    assert len(CANONICAL_FAMILIES) == 10
    assert AttackFamily.BENIGN.value == "benign"
    assert AttackFamily.UNKNOWN_SUSPICIOUS.value == "unknown_suspicious"
    assert AttackFamily.DOS.value == "dos"
    assert AttackFamily.DDOS.value == "ddos"
    assert AttackFamily.BRUTE_FORCE.value == "brute_force"
    assert AttackFamily.PORT_SCAN_RECON.value == "port_scan_recon"
    assert AttackFamily.BOTNET.value == "botnet"
    assert AttackFamily.WEB_ATTACK.value == "web_attack"
    assert AttackFamily.INFILTRATION.value == "infiltration"
    assert AttackFamily.EXPLOIT_OTHER.value == "exploit_other"


def test_family_id_bidirectional_mapping() -> None:
    for fam in CANONICAL_FAMILIES:
        cid = family_to_id(fam)
        assert id_to_family(cid) == fam


def test_is_attack_family() -> None:
    assert not is_attack_family("benign")
    assert is_attack_family("dos")
    assert is_attack_family("ddos")
    assert is_attack_family("unknown_suspicious")


def test_taxonomy_mapper_cic() -> None:
    mapper = TaxonomyMapper()
    fam, subtype, l1 = mapper.map_label("cic", "BENIGN")
    assert fam == "benign"
    assert subtype == "normal"
    assert l1 == 0

    fam, subtype, l1 = mapper.map_label("cic", "DoS Hulk")
    assert fam == "dos"
    assert subtype == "dos_hulk"
    assert l1 == 1

    fam, subtype, l1 = mapper.map_label("cic", "PortScan")
    assert fam == "port_scan_recon"
    assert l1 == 1

    fam, subtype, l1 = mapper.map_label("cic", "SSH-Patator")
    assert fam == "brute_force"
    assert l1 == 1


def test_taxonomy_mapper_unsw() -> None:
    mapper = TaxonomyMapper()
    fam, subtype, l1 = mapper.map_label("unsw", "Normal")
    assert fam == "benign"
    assert l1 == 0

    fam, subtype, l1 = mapper.map_label("unsw", "Fuzzers")
    assert fam == "port_scan_recon"
    assert l1 == 1

    fam, subtype, l1 = mapper.map_label("unsw", "Backdoors")
    assert fam == "botnet"
    assert l1 == 1


def test_taxonomy_mapper_kdd() -> None:
    mapper = TaxonomyMapper()
    fam, subtype, l1 = mapper.map_label("kdd", "normal")
    assert fam == "benign"
    assert l1 == 0

    fam, subtype, l1 = mapper.map_label("kdd", "neptune")
    assert fam == "dos"
    assert l1 == 1

    fam, subtype, l1 = mapper.map_label("kdd", "guess_passwd")
    assert fam == "brute_force"
    assert l1 == 1


def test_taxonomy_mapper_unknown_label_honesty() -> None:
    """Honesty Rule: Unrecognized raw label must map to unknown_suspicious."""
    mapper = TaxonomyMapper()
    fam, subtype, l1 = mapper.map_label("cic", "ZeroDayAlienExploit")
    assert fam == AttackFamily.UNKNOWN_SUSPICIOUS.value
    assert "unmapped" in subtype
    assert l1 == 1
