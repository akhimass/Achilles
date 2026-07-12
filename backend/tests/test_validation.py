"""Tests for the self-validation ('prove-it') engine. No DB, no network, no LLM.

Locks the two properties that beat a search box: recall (recovers a grounded known-true
control) and precision (refuses a known-false control; fabrications must be 0).
"""

from __future__ import annotations

from app.ingestion.validation import evaluate

_BENCH = {
    "organism": "Test org",
    "positives": [
        {"gene": "MarR", "locus": "L1", "relation": "confers_resistance",
         "target_terms": ["ciprofloxacin"], "citation": "CARD:ARO:1"},
        {"gene": "MarR", "locus": "L1", "relation": "implicates",
         "target_terms": ["efflux"], "citation": "CARD:ARO:2"},
        {"gene": "X", "locus": "L9", "relation": "confers_resistance",
         "target_terms": ["nothing-here"], "citation": "CARD:ARO:9"},
    ],
    "negatives": [
        {"gene": "MarR", "locus": "L1", "relation": "confers_resistance",
         "target_terms": ["vancomycin"], "reason": "false"},
    ],
}

_EDGES = [
    {"locus": "L1", "relation": "confers_resistance", "target": "ciprofloxacin resistance",
     "grounded": True, "provenance": {"db": "CARD", "acc": "ARO:1"}},
    {"locus": "L1", "relation": "implicates", "target": "efflux pump regulation",
     "grounded": False, "provenance": {"pmid": "111"}},  # abstract-only → literature_only
]


def test_recovers_refuses_and_scores():
    rep = evaluate(_BENCH, _EDGES)
    by = {(i.locus, i.relation, tuple(i.target_terms)): i for i in rep.items}
    # grounded positive → recovered, carries its provenance
    rec = by[("L1", "confers_resistance", ("ciprofloxacin",))]
    assert rec.status == "recovered" and rec.grounded is True
    assert rec.provenance.get("acc") == "ARO:1"
    # abstract-only positive → literature_only (honest partial)
    assert by[("L1", "implicates", ("efflux",))].status == "literature_only"
    # positive with no edge → missing
    assert by[("L9", "confers_resistance", ("nothing-here",))].status == "missing"
    # false negative control has no grounded edge → refused (not fabricated)
    assert by[("L1", "confers_resistance", ("vancomycin",))].status == "refused"

    m = rep.metrics
    assert m["positives"] == 3 and m["recovered"] == 1 and m["literature_only"] == 1 and m["missing"] == 1
    assert m["negatives"] == 1 and m["refused"] == 1
    assert m["fabricated"] == 0 and m["clean"] is True


def test_fabrication_is_flagged():
    # If a grounded edge asserts a known-FALSE control, it must be caught as fabricated.
    edges = _EDGES + [
        {"locus": "L1", "relation": "confers_resistance", "target": "vancomycin resistance",
         "grounded": True, "provenance": {"db": "CARD", "acc": "BAD"}},
    ]
    rep = evaluate(_BENCH, edges)
    neg = next(i for i in rep.items if i.kind == "negative")
    assert neg.status == "fabricated"
    assert rep.metrics["fabricated"] == 1 and rep.metrics["clean"] is False


def test_committed_benchmark_is_wellformed():
    from app.ingestion.validation import load_benchmark

    b = load_benchmark()
    assert b["positives"] and b["negatives"]
    # every positive carries a public citation; every negative a reason.
    assert all(p.get("citation") for p in b["positives"])
    assert all(n.get("reason") for n in b["negatives"])
