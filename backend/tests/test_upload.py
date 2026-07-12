"""Tests for bring-your-own-strains ingestion + the cycling 'next experiment' CTA.
Deterministic — no DB, no network, no LLM."""

from __future__ import annotations

import pytest

from app.ingestion.upload import UploadError, build_upload_graph, parse_profiles
from app.models.domain import CollateralPair
from app.treatment_shaping import next_experiment

# A tiny MLST-style table: id + 4 loci + year. gyrB toggles across isolates.
_CSV = """id,atpD,gltB,gyrB,recA,year
iso1,1,1,1,1,2001
iso2,1,1,2,1,2003
iso3,1,1,1,1,2005
iso4,1,1,2,1,2007
iso5,2,1,1,1,2009
"""


def test_parse_profiles_detects_id_loci_and_meta():
    records, loci, _ = parse_profiles(_CSV)
    assert len(records) == 5
    assert set(loci) == {"atpD", "gltB", "gyrB", "recA"}  # 'year' excluded as metadata
    assert records[0]["id"] == "iso1"
    assert records[0]["year"] == 2001
    # alleles are integer-coded
    assert all(isinstance(v, int) for v in records[0]["profile"].values())


def test_build_upload_graph_shape_is_a_tree():
    g = build_upload_graph(_CSV)
    assert len(g["nodes"]) == 5
    assert len(g["edges"]) == 4  # a spanning tree over 5 nodes
    assert g["summary"]["roots"] == 1
    assert g["summary"]["loci"] == 4
    # every node id is stringified and every edge references known nodes
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert all(isinstance(n["flipper_count"], int) for n in g["nodes"])


def test_upload_rejects_too_few_and_missing_genotype():
    with pytest.raises(UploadError):
        parse_profiles("id,gyrB,year\niso1,1,2001\n")  # < 3 isolates
    with pytest.raises(UploadError):
        parse_profiles("id,year,country\niso1,2001,US\niso2,2002,UK\niso3,2003,DE\n")  # no loci


def test_upload_dedupes_ids_deterministically():
    csv = "id,g1,g2\nA,1,1\nA,2,2\nB,1,2\nC,2,1\n"  # duplicate A → first wins
    records, _, warnings = parse_profiles(csv)
    ids = [r["id"] for r in records]
    assert ids.count("A") == 1
    assert warnings.get("dropped_rows", 0) >= 1


def test_next_experiment_picks_strongest_reciprocal():
    cycle = ["SXT", "MEM", "CAZ"]
    pairs = [
        CollateralPair(organism="x", drug_a="SXT", drug_b="MEM", reciprocal=True, n_lineages=5),
        CollateralPair(organism="x", drug_a="MEM", drug_b="CAZ", reciprocal=True, n_lineages=2),
    ]
    exp = next_experiment(cycle, pairs)  # pairs pre-sorted by support in shape_cycle
    assert exp is not None
    assert exp["drug_a"] == "SXT" and exp["drug_b"] == "MEM"
    assert exp["n_lineages"] == 5
    assert "SXT" in exp["headline"] and "MEM" in exp["headline"]


def test_next_experiment_none_when_no_cycle():
    assert next_experiment([], []) is None
    assert next_experiment(["A", "B"], []) is None
