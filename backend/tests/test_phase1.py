"""Phase 1 tests — deterministic transforms for the lineage/flipper pipeline.

No DB, no network, no API key. These lock the new spine: BV-BRC record mapping,
MLST variant construction, MST lineage reconstruction, MLST flipper detection, the
lineage-graph shaping, and the whole pipeline over the real committed demo snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.graph_shaping import shape_lineage
from app.ingestion.flippers import build_lineage_paths, detect_mlst_flippers
from app.ingestion.lineage import allelic_distance, build_mst_lineage
from app.ingestion.parsers import (
    MLST_LOCI,
    mlst_reference_alleles,
    mlst_variant_table,
    parse_variant_table,
)
from app.sources.bvbrc import _map_genome_record

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "demo" / "bmultivorans_pubmlst.json"


# ─── BV-BRC → Strain mapping ─────────────────────────────────────────────────


def test_bvbrc_map_genome_record():
    # Documented BV-BRC genome record shape.
    rec = {
        "genome_id": "87883.42",
        "genome_name": "Burkholderia multivorans strain ATCC 17616",
        "strain": "ATCC 17616",
        "taxon_id": 87883,
        "genome_status": "Complete",
        "genome_length": 7008000,
        "collection_year": 1966,
        "isolation_country": "USA",
        "host_name": "soil",
    }
    s = _map_genome_record(rec, "Burkholderia multivorans")
    assert s.external_id == "87883.42"
    assert s.source == "bvbrc"
    assert s.organism == "Burkholderia multivorans"
    assert s.label == "ATCC 17616"  # prefers strain over genome_name
    assert s.metadata["collection_year"] == 1966
    assert s.metadata["country"] == "USA"
    # nulls are dropped from metadata
    assert "geographic_group" not in s.metadata


def test_bvbrc_map_falls_back_to_genome_name_for_label():
    rec = {"genome_id": "1.1", "genome_name": "B. multivorans X"}
    s = _map_genome_record(rec, "Burkholderia multivorans")
    assert s.label == "B. multivorans X"


# ─── MLST variant table ──────────────────────────────────────────────────────


def test_mlst_reference_alleles_is_modal():
    profiles = [
        {"atpD": 1}, {"atpD": 1}, {"atpD": 2},  # 1 is modal at atpD
    ]
    ref = mlst_reference_alleles(profiles)
    assert ref["atpD"] == 1


def test_mlst_variant_table_maps_to_variants():
    profile = {L: i + 1 for i, L in enumerate(MLST_LOCI)}
    ref = {L: 1 for L in MLST_LOCI}
    strain_id = uuid4()
    df = mlst_variant_table(profile, ref)
    variants = parse_variant_table(df, strain_id)
    assert len(variants) == 7
    v = {x.metadata["locus"]: x for x in variants}
    assert v["gyrB"].alt_allele == "3"  # gyrB is 3rd locus -> allele 3
    assert v["gyrB"].ref_allele == "1"
    assert v["gyrB"].allele_freq == 1.0
    assert v["gyrB"].metadata["encoding"] == "mlst_allele"
    assert all(x.kind.value == "snp" for x in variants)


# ─── MST lineage reconstruction ──────────────────────────────────────────────


def _rec(rid, year, profile):
    return {"id": rid, "year": year, "profile": profile}


def test_build_mst_lineage_is_a_single_rooted_tree():
    records = [
        _rec(1, 1990, {L: 1 for L in MLST_LOCI}),
        _rec(2, 1991, {**{L: 1 for L in MLST_LOCI}, "gyrB": 2}),  # 1 step from #1
        _rec(3, 1992, {**{L: 1 for L in MLST_LOCI}, "gyrB": 2, "recA": 5}),  # 1 step from #2
        _rec(4, 1993, {L: 9 for L in MLST_LOCI}),  # far from all
    ]
    parent = build_mst_lineage(records)
    roots = [k for k, v in parent.items() if v is None]
    assert roots == [1]  # earliest year is the root
    assert set(parent) == {1, 2, 3, 4}
    assert parent[2] == 1  # nearest neighbor
    assert parent[3] == 2
    # every non-root points at a real node; no cycles (each has a shorter path to root)
    for node in parent:
        seen = set()
        cur = node
        while parent[cur] is not None:
            assert cur not in seen
            seen.add(cur)
            cur = parent[cur]
        assert cur == 1


def test_build_mst_lineage_deterministic():
    records = [_rec(i, 1990 + i, {L: (i % 3) + 1 for L in MLST_LOCI}) for i in range(6)]
    assert build_mst_lineage(records) == build_mst_lineage(list(reversed(records)))


def test_allelic_distance():
    a = {L: 1 for L in MLST_LOCI}
    b = {**a, "gyrB": 2, "recA": 3}
    assert allelic_distance(a, b) == 2
    assert allelic_distance(a, a) == 0


# ─── MLST flipper detection ──────────────────────────────────────────────────


def test_detect_mlst_flipper_reversal():
    # Linear lineage a->b->c->d; gyrB allele goes 1 -> 2 -> 1 (reversal).
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    paths = build_lineage_paths({a: None, b: a, c: b, d: c})
    profiles = {
        a: {"gyrB": 1, "recA": 1},
        b: {"gyrB": 2, "recA": 1},
        c: {"gyrB": 1, "recA": 1},  # gyrB reverts to 1
        d: {"gyrB": 1, "recA": 1},
    }
    per_strain = detect_mlst_flippers(profiles, paths)
    all_sites = {pair for sites in per_strain.values() for pair in sites}
    assert ("gyrB", 1) in all_sites
    assert ("recA", 1) not in all_sites  # never changes -> not a flipper
    # the reversal runs through the whole path, so carrier strains are attributed it
    assert ("gyrB", 1) in per_strain[a]


# ─── Lineage graph shaping ───────────────────────────────────────────────────


def test_shape_lineage_nodes_and_edges():
    rows = [
        {"id": "r", "label": "root", "parent_id": None, "flipper_count": 0},
        {"id": "a", "label": "A", "parent_id": "r", "flipper_count": 3, "st": 15},
        {"id": "b", "label": "B", "parent_id": "missing", "flipper_count": 1},
    ]
    g = shape_lineage(rows)
    assert len(g["nodes"]) == 3
    # edge from r->a only; b's parent isn't in the node set -> dropped
    assert {"source": "r", "target": "a"} in g["edges"]
    assert len(g["edges"]) == 1
    assert g["nodes"][1]["st"] == 15


# ─── End-to-end over the real committed snapshot ─────────────────────────────


def test_build_dataset_over_real_snapshot():
    from app.ingestion.seed import build_dataset

    records = json.loads(SNAPSHOT.read_text())["records"]
    assert len(records) >= 40  # real dataset present
    strains, variants, n_flip_sites = build_dataset(records)

    assert len(strains) == len(records)
    assert len(variants) == 7 * len(records)  # 7 MLST loci per strain

    # exactly one root; every parent references a real strain
    ids = {s.id for s in strains}
    roots = [s for s in strains if s.parent_id is None]
    assert len(roots) == 1
    assert all(s.parent_id in ids for s in strains if s.parent_id is not None)

    # flippers actually detected over the real reconstructed lineage
    assert n_flip_sites > 0
    assert any(v.is_flipper for v in variants)

    # every variant is annotated with a gene and carries the MLST encoding
    assert all(v.gene_id is not None for v in variants)
    assert all(v.metadata.get("encoding") == "mlst_allele" for v in variants)
