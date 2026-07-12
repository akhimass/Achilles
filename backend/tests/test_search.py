"""Tests for the deterministic search ranker/shaper. No DB, no network, no LLM.

Locks: results are grounded (carry provenance), ranking is relevance-ordered and
input-order independent, zero-relevance candidates are dropped (never padded), and the
payload reports honest counts.
"""

from __future__ import annotations

from app.search_shaping import (
    edge_candidate,
    gene_candidate,
    paper_candidate,
    rank_results,
    shape_search,
    tokenize,
)


def _candidates() -> list[dict]:
    return [
        paper_candidate({"pmid": "222", "title": "MarR regulates efflux and resistance",
                         "abstract": "MarR mutations confer ciprofloxacin resistance.", "year": 2021}),
        paper_candidate({"pmid": "999", "title": "Unrelated ribosome assembly study",
                         "abstract": "A structural analysis of subunit docking.", "year": 2010}),
        gene_candidate({"locus_tag": "A8H40_RS07590", "name": "MarR",
                        "product": "MarR family regulator", "uniprot_acc": "A0A0H3KEU2"}),
        edge_candidate({"id": "e1", "relation": "confers_resistance", "target_literal": "ciprofloxacin",
                        "grounded": True, "confidence": 0.95, "provenance_pmid": "222",
                        "provenance_db": "CARD", "provenance_acc": "ARO:3003378",
                        "metadata": {"subject": "MarR", "evidence_span": "MarR confers ciprofloxacin resistance",
                                     "gene_locus": "A8H40_RS07590"}}),
    ]


def test_tokenize():
    assert tokenize("MarR, efflux-pump!") == ["marr", "efflux", "pump"]


def test_ranks_relevant_grounded_first_and_drops_zero():
    res = rank_results("MarR efflux", _candidates())
    kinds_ids = [(r["kind"], r["id"]) for r in res]
    # The unrelated ribosome paper (pmid 999) has no query-term hits → dropped.
    assert ("paper", "999") not in kinds_ids
    # Every returned result is relevant and carries provenance.
    assert all(r["score"] > 0 for r in res)
    assert all("provenance" in r for r in res)
    # The MarR gene + MarR paper + MarR edge all surface.
    assert {"A8H40_RS07590", "222", "e1"} <= {str(r["id"]) for r in res}


def test_ranking_is_input_order_independent():
    cands = _candidates()
    a = [(r["kind"], r["id"], r["score"]) for r in rank_results("resistance MarR", cands)]
    b = [(r["kind"], r["id"], r["score"]) for r in rank_results("resistance MarR", list(reversed(cands)))]
    assert a == b


def test_grounded_boost_and_snippet():
    res = rank_results("ciprofloxacin", _candidates())
    top = res[0]
    assert top["grounded"] is True
    assert top["snippet"] and "ciprofloxacin" in top["snippet"].lower()


def test_shape_search_reports_counts_and_mode():
    out = shape_search("MarR resistance", _candidates(), mode="lexical")
    assert out["query"] == "MarR resistance" and out["mode"] == "lexical"
    assert out["counts"]["total"] == len(out["results"])
    assert out["counts"]["grounded"] >= 1
    assert set(out["counts"]["by_kind"]) <= {"paper", "gene", "edge"}
    # Empty query-term overlap → no results, honest zero counts.
    empty = shape_search("zzzznomatch", _candidates())
    assert empty["results"] == [] and empty["counts"]["total"] == 0
