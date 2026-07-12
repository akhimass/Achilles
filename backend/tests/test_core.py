"""Tests for the deterministic core — no DB, no network, no API key needed.

These lock the two things that must never regress: flipper detection reverses
correctly, and no evidence edge can exist without provenance.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.ingestion.collateral import (
    SensitivityObservation,
    compute_collateral_pairs,
    propose_cycle,
)
from app.ingestion.flippers import build_lineage_paths, detect_flippers
from app.models.domain import EvidenceEdge, NodeType, Relation, Variant, VariantKind


def _v(strain_id, pos, af):
    return Variant(
        strain_id=strain_id, kind=VariantKind.snp, ref_position=pos, allele_freq=af
    )


def test_detect_flipper_reversal():
    # Linear lineage a -> b -> c -> d; position 100 goes present/absent/present.
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    parent_of = {a: None, b: a, c: b, d: c}
    paths = build_lineage_paths(parent_of)
    variants_by_strain = {
        a: [_v(a, 100, 0.9)],  # present
        b: [_v(b, 100, 0.0)],  # absent
        c: [_v(c, 100, 0.9)],  # present again -> reversal
        d: [_v(d, 100, 0.9)],
    }
    sites = detect_flippers(variants_by_strain, paths)
    assert len(sites) == 1
    assert sites[0].ref_position == 100
    assert sites[0].transitions >= 2


def test_no_flipper_when_monotonic():
    a, b, c = uuid4(), uuid4(), uuid4()
    paths = build_lineage_paths({a: None, b: a, c: b})
    variants = {a: [_v(a, 50, 0.0)], b: [_v(b, 50, 0.9)], c: [_v(c, 50, 0.9)]}
    assert detect_flippers(variants, paths) == []


def test_reciprocal_cs_and_cycle():
    obs = [
        SensitivityObservation("L1", "MEM", "CHL"),
        SensitivityObservation("L2", "CHL", "MEM"),  # reciprocal with above
        SensitivityObservation("L3", "CHL", "LVX"),
    ]
    pairs = compute_collateral_pairs(obs, "Burkholderia multivorans")
    rcs = [p for p in pairs if p.reciprocal]
    assert {(p.drug_a, p.drug_b) for p in rcs} == {("MEM", "CHL"), ("CHL", "MEM")}
    cycle = propose_cycle(pairs)
    assert set(cycle) <= {"MEM", "CHL"} and len(cycle) >= 2


def test_edge_requires_provenance():
    with pytest.raises(ValueError):
        EvidenceEdge(
            source_type=NodeType.variant,
            source_id=uuid4(),
            relation=Relation.confers_resistance,
            target_type=NodeType.drug,
            target_literal="meropenem",
            confidence=0.8,
        )  # no provenance_pmid and no provenance_acc -> must fail


def test_edge_with_provenance_ok():
    e = EvidenceEdge(
        source_type=NodeType.variant,
        source_id=uuid4(),
        relation=Relation.confers_resistance,
        target_type=NodeType.drug,
        target_literal="meropenem",
        provenance_pmid="12345678",
        confidence=0.8,
    )
    assert e.provenance_pmid == "12345678"
