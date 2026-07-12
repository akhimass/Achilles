"""Tests for the BurkData demo pipeline and the Tamarind structure parser.

Deterministic, no DB / network / API key. Locks: the real experimental lineage
seeds a single-root-per-founder forest, indel flippers are detected along the real
lineages, gene products resolve, and pLDDT parsing is correct.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ai.tamarind import plddt_from_pdb, residue_count_from_pdb
from app.graph_shaping import shape_lineage
from app.ingestion.seed import build_burk_dataset

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "demo" / "bmultivorans_burkdata.json"

# BurkData is private (local-only, gitignored). These tests exercise the local demo
# path and are skipped where the private snapshot is absent (e.g. a public clone).
pytestmark = pytest.mark.skipif(
    not SNAPSHOT.exists(), reason="private BurkData snapshot not present (public checkout)"
)


def _records() -> dict:
    return json.loads(SNAPSHOT.read_text())


def test_burk_dataset_shape():
    strains, genes, variants, n_sites = build_burk_dataset(_records())
    assert len(strains) == 47
    assert len(genes) == 60
    assert len(variants) > 500
    assert n_sites > 0
    # every non-founder parent references a real strain
    ids = {s.id for s in strains}
    assert all(s.parent_id in ids for s in strains if s.parent_id is not None)
    # the 8 experimental founders are the roots
    roots = sorted(s.label for s in strains if s.parent_id is None)
    assert roots == ["167", "170", "172", "177", "183", "184", "195", "210"]


def test_burk_founder_carries_real_resistance():
    strains, *_ = build_burk_dataset(_records())
    founder = next(s for s in strains if s.label == "167")
    assert founder.metadata["founder"] is True
    assert "MIN" in founder.metadata.get("resistance", [])
    assert "CAZ" in founder.metadata.get("sensitivity", [])
    assert "L1" in founder.metadata["lineages"]


def test_burk_genes_have_products_and_flippers_detected():
    strains, genes, variants, _ = build_burk_dataset(_records())
    assert all(g.product for g in genes)  # every flipper gene resolved a product
    # the MarR regulator (AlphaFold showcase) is in the set
    marr = [g for g in genes if g.locus_tag == "A8H40_RS07590"]
    assert marr and "MarR" in (marr[0].product or "")
    # flippers actually detected across the real lineages
    assert any(v.is_flipper for v in variants)
    # indels that aren't multiples of 3 are annotated frameshift
    fs = [v for v in variants if v.metadata["indel_delta"] % 3 != 0]
    assert fs and all(v.effect and v.effect.value == "frameshift" for v in fs)


def test_shape_lineage_carries_burk_fields():
    rows = [
        {"id": "a", "label": "167", "parent_id": None, "flipper_count": 5,
         "lineage": "L1, L2", "founder": True},
        {"id": "b", "label": "515", "parent_id": "a", "flipper_count": 3,
         "lineage": "L1", "founder": False},
    ]
    g = shape_lineage(rows)
    assert g["nodes"][0]["lineage"] == "L1, L2"
    assert g["nodes"][0]["founder"] is True
    assert g["nodes"][1]["founder"] is False
    assert {"source": "a", "target": "b"} in g["edges"]


def test_plddt_and_residue_parsing():
    pdb = "\n".join(
        [
            "ATOM      1  N   MET A   1      11.104  13.207  10.567  1.00 90.50           N",
            "ATOM      2  CA  MET A   1      12.560  13.100  10.500  1.00 70.50           C",
            "ATOM      3  N   ALA A   2      13.000  14.000  11.000  1.00 80.00           N",
        ]
    )
    assert plddt_from_pdb(pdb) == 80.3  # mean of 90.5, 70.5, 80.0
    assert residue_count_from_pdb(pdb) == 2
