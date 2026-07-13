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


def test_resolve_locus_accepts_name_or_tag():
    from app.ingestion.validation import resolve_locus

    assert resolve_locus("MarR") == "A8H40_RS07590"
    assert resolve_locus("efflux") == "A8H40_RS19975"
    assert resolve_locus("A8H40_RS07590") == "A8H40_RS07590"
    assert resolve_locus("not-a-gene") is None


def test_redteam_supports_true_refuses_false_and_flags_weak():
    from app.ingestion.validation import adjudicate

    edges = [
        {"locus": "A8H40_RS07590", "relation": "confers_resistance", "target": "ciprofloxacin",
         "grounded": True, "provenance": {"db": "CARD", "acc": "ARO:3003378"}},
        {"locus": "A8H40_RS07590", "relation": "implicates", "target": "tigecycline response",
         "grounded": False, "provenance": {"pmid": "41822337"}},
    ]
    # True claim → supported, with its grounded citation.
    yes = adjudicate("MarR", "ciprofloxacin", edges)
    assert yes["verdict"] == "supported" and yes["grounded"] is True
    assert yes["provenance"]["acc"] == "ARO:3003378"
    # Planted-false claim → refused, not fabricated.
    no = adjudicate("MarR", "vancomycin", edges)
    assert no["verdict"] == "refused" and no["grounded"] is False
    # Abstract-only mention → weak (not asserted as validated).
    weak = adjudicate("MarR", "tigecycline", edges)
    assert weak["verdict"] == "weak" and weak["grounded"] is False
    # Unknown gene → honest 'unknown_gene', never a guess.
    assert adjudicate("phlogiston", "anything", edges)["verdict"] == "unknown_gene"


def test_committed_benchmark_is_wellformed():
    from app.ingestion.validation import load_benchmark

    b = load_benchmark()
    assert b["positives"] and b["negatives"]
    # every positive carries a public citation; every negative a reason.
    assert all(p.get("citation") for p in b["positives"])
    assert all(n.get("reason") for n in b["negatives"])


def test_scaled_benchmark_is_clean_against_the_real_corpus():
    """The headline invariant, at scale: against the real grounded graph the committed
    benchmark must recover every positive and REFUSE every adversarial negative with
    zero fabrications. Guards Track A — a future benchmark edit can't silently break it.
    """
    import json
    from pathlib import Path

    from app.ingestion.validation import load_benchmark

    root = Path(__file__).resolve().parents[2]
    corpus = json.loads((root / "data/demo/literature/corpus.json").read_text())
    edges = []
    for e in corpus.get("edges", []):
        loc = e.get("gene_locus") or (e.get("metadata") or {}).get("gene_locus")
        if not loc:
            continue
        edges.append({
            "locus": loc, "relation": e.get("relation"), "target": e.get("target_literal"),
            "grounded": bool(e.get("grounded")), "provenance": {"pmid": e.get("provenance_pmid")},
        })

    b = load_benchmark()
    m = evaluate(b, edges).metrics
    # scale floors so the battery can't silently shrink below what we ship
    assert m["positives"] >= 12 and m["negatives"] >= 17
    assert m["recovered"] == m["positives"], "every positive must recover"
    assert m["refused"] == m["negatives"], "every adversarial negative must be refused"
    assert m["fabricated"] == 0 and m["clean"] is True
