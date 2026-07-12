"""Public cited collateral-sensitivity + strain-anchored cycling — pure checks.

Proves the treatment beat renders from redistributable, cited data (so it isn't blank
on the public deploy) and that anchoring starts the cycle at a chosen drug — without a
database.
"""

from __future__ import annotations

from app.ingestion.collateral import propose_cycle
from app.ingestion.seed_collateral import load_public_cs_pairs
from app.treatment_shaping import next_experiment, shape_cycle


def test_public_pairs_are_cited_and_reciprocal():
    pairs = load_public_cs_pairs()
    assert pairs, "expected public cited CS pairs to load"
    # Every public pair is reciprocal and carries a PMID (never uncited).
    assert all(p.reciprocal for p in pairs)
    assert all((p.metadata or {}).get("pmid") for p in pairs)
    # Both directions are present for each reciprocal pair.
    directed = {(p.drug_a, p.drug_b) for p in pairs}
    assert ("meropenem", "levofloxacin") in directed
    assert ("levofloxacin", "meropenem") in directed


def test_public_data_yields_a_cycle():
    cycle = propose_cycle(load_public_cs_pairs())
    assert len(cycle) >= 3, "cited public pairs should support a multi-drug cycle"


def test_anchor_starts_the_cycle_at_the_chosen_drug():
    pairs = load_public_cs_pairs()
    cycle = propose_cycle(pairs, starts={"ceftazidime"})
    assert cycle and cycle[0] == "ceftazidime"
    # A drug not in the reciprocal graph anchors nothing.
    assert propose_cycle(pairs, starts={"vancomycin"}) == []


def test_shape_surfaces_citation_and_anchor():
    pairs = load_public_cs_pairs()
    cycle = propose_cycle(pairs, starts={"meropenem"})
    anchor = {"anchored": True, "strain": "CF-lineage-A", "matched": ["meropenem"],
              "requested": ["meropenem"], "unmatched": [], "reason": "anchored to meropenem"}
    shaped = shape_cycle("Burkholderia multivorans", cycle, pairs, anchor=anchor)
    assert shaped["anchor"]["anchored"] is True
    assert shaped["counts"]["cited"] == shaped["counts"]["reciprocal"]  # all cited
    assert all(p["provenance"] and p["provenance"]["pmid"] for p in shaped["rcs_pairs"])
    # Every hop of the cycle carries provenance too.
    assert all(s["provenance"] and s["provenance"]["pmid"] for s in shaped["steps"])


def test_next_experiment_cites_literature_when_no_lineage_count():
    pairs = load_public_cs_pairs()
    cycle = propose_cycle(pairs)
    reciprocal = [p for p in pairs if p.reciprocal]
    nx = next_experiment(cycle, reciprocal)
    assert nx and nx["provenance"] and nx["provenance"]["pmid"] == "32335276"
    assert "PMID 32335276" in nx["detail"]
    assert "evolved lineage" not in nx["detail"]  # no fabricated lineage count
