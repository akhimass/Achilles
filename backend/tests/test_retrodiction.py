"""Retrodiction (time-split foresight) — pure, deterministic checks.

Synthetic cases pin each status; the corpus case proves the real demo claim holds
(AraC/MarA anticipates the 2020 tigecycline confirmation from a 2019 cutoff) without
touching a database — the same edge shape the router builds is reconstructed offline.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.validation import retrodict

_ROOT = Path(__file__).resolve().parents[2]


def _edge(locus, relation, target, grounded, year):
    return {"locus": locus, "relation": relation, "target": target,
            "grounded": grounded, "year": year, "provenance": {"pmid": "x"}}


def _bench(positives, negatives=None):
    return {"organism": "test", "positives": positives, "negatives": negatives or []}


def test_known_by_cutoff_is_not_a_win():
    bench = _bench([{"gene": "G", "locus": "L1", "relation": "confers_resistance",
                     "target_terms": ["tigecycline"]}])
    edges = [_edge("L1", "confers_resistance", "tigecycline resistance", True, 2015)]
    rep = retrodict(bench, edges, cutoff=2019)
    assert rep["positives"][0]["status"] == "known_by_cutoff"
    assert rep["metrics"]["anticipated"] == 0
    assert rep["metrics"]["held_out"] == 0


def test_anticipated_mechanism():
    # Grounded drug confirmation is post-cutoff (2020); a pre-cutoff grounded
    # resistance-driver edge on the same gene supplies mechanism-level foresight.
    bench = _bench([{"gene": "G", "locus": "L1", "relation": "confers_resistance",
                     "target_terms": ["tigecycline"]}])
    edges = [
        _edge("L1", "confers_resistance", "multidrug resistance", True, 2013),
        _edge("L1", "confers_resistance", "tigecycline resistance", True, 2020),
    ]
    rep = retrodict(bench, edges, cutoff=2019)
    p = rep["positives"][0]
    assert p["status"] == "anticipated_mechanism"
    assert p["confirm_year"] == 2020
    assert p["pre_cutoff_signal"] and p["pre_cutoff_signal"][0]["year"] == 2013
    assert rep["metrics"]["anticipated"] == 1


def test_anticipated_drug_beats_mechanism():
    # A pre-cutoff edge naming the same drug is stronger (drug-level foresight).
    bench = _bench([{"gene": "G", "locus": "L1", "relation": "confers_resistance",
                     "target_terms": ["tigecycline"]}])
    edges = [
        _edge("L1", "implicates", "tigecycline response", False, 2018),  # abstract-only, named
        _edge("L1", "confers_resistance", "tigecycline resistance", True, 2020),
    ]
    rep = retrodict(bench, edges, cutoff=2019)
    assert rep["positives"][0]["status"] == "anticipated_drug"


def test_not_anticipable_is_honest():
    # Post-cutoff confirmation with zero pre-cutoff signal → we could NOT have called it.
    bench = _bench([{"gene": "G", "locus": "L1", "relation": "confers_resistance",
                     "target_terms": ["tigecycline"]}])
    edges = [_edge("L1", "confers_resistance", "tigecycline resistance", True, 2024)]
    rep = retrodict(bench, edges, cutoff=2019)
    assert rep["positives"][0]["status"] == "not_anticipable"
    assert rep["metrics"]["anticipated"] == 0


def test_false_claim_is_never_anticipated():
    # A negative control with a grounded resistance edge on the gene must NOT be
    # "anticipated" — the confirming edge for the false target never exists.
    bench = _bench(
        positives=[],
        negatives=[{"gene": "G", "locus": "L1", "relation": "confers_resistance",
                    "target_terms": ["vancomycin"]}],
    )
    edges = [_edge("L1", "confers_resistance", "multidrug resistance", True, 2013)]
    rep = retrodict(bench, edges, cutoff=2019)
    assert rep["metrics"]["false_anticipations"] == 0
    assert rep["metrics"]["clean"] is True


def test_corpus_demo_case_holds():
    """Real data: from a 2019 cutoff, AraC/MarA (RS24275) anticipates its later
    grounded resistance confirmation via pre-2020 grounded efflux/MDR edges."""
    corpus = json.loads((_ROOT / "data/demo/literature/corpus.json").read_text())
    bench = json.loads((_ROOT / "data/demo/benchmark/known_relationships.json").read_text())
    papers = {p["pmid"]: p for p in corpus.get("papers", [])}
    edges = []
    for e in corpus.get("edges", []):
        locus = e.get("gene_locus") or (e.get("metadata") or {}).get("gene_locus")
        if not locus:
            continue
        edges.append({
            "locus": locus, "relation": e.get("relation"),
            "target": e.get("target_literal"), "grounded": bool(e.get("grounded")),
            "year": papers.get(e.get("provenance_pmid"), {}).get("year"),
            "provenance": {"pmid": e.get("provenance_pmid")},
        })
    rep = retrodict(bench, edges, cutoff=2019)
    # Foresight without fabrication is the invariant we ship on.
    assert rep["metrics"]["false_anticipations"] == 0
    # At least one AraC/MarA positive is anticipated from the pre-2020 graph.
    araca = [p for p in rep["positives"]
             if p["locus"] == "A8H40_RS24275" and p["status"].startswith("anticipated")]
    assert araca, "expected AraC/MarA to be anticipated at cutoff 2019"
    assert any(p["confirm_year"] and p["confirm_year"] > 2019 for p in araca)
