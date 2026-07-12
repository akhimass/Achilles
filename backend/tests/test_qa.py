"""Grounded Q&A core — pure checks. The anti-slop invariants:
recall only what's grounded, refuse when nothing is, and never fabricate.
"""

from __future__ import annotations

from app.qa import build_answer, citation_label, detect_intent, normalize_persona


def _res(kind, title, grounded, *, relation=None, conf=None, pmid=None, db=None, acc=None):
    return {
        "kind": kind, "title": title, "snippet": title, "score": 1.0, "grounded": grounded,
        "provenance": {"pmid": pmid, "pubmed_url": pmid and f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                       "db": db, "acc": acc, "ref_url": None},
        "extra": {"relation": relation, "confidence": conf, "gene_locus": "A8H40_RS07590"},
    }


def test_intent_detection():
    assert detect_intent("what cycle should follow meropenem resistance") == "treatment"
    assert detect_intent("is MarR a druggable target") == "target"
    assert detect_intent("what's the citation for this claim") == "provenance"
    assert detect_intent("how does efflux confer resistance") == "mechanism"
    assert detect_intent("tell me about burkholderia") == "general"


def test_persona_normalization():
    assert normalize_persona("Physician") == "physician"
    assert normalize_persona("nonsense") == "researcher"
    assert normalize_persona(None) == "researcher"


def test_refuses_when_no_grounded_evidence():
    results = [_res("edge", "some abstract-only mention", False)]
    ans = build_answer("does MarR confer vancomycin resistance", "researcher", results)
    assert ans["refused"] is True
    assert ans["grounded"] is False
    assert ans["claims"] == []
    assert ans["answer"] is None
    assert "refuses" in ans["deterministic_summary"].lower()


def test_builds_cited_claims_from_grounded_results():
    results = [
        _res("edge", "MarR implicates efflux", True, relation="implicates", conf=0.9,
             db="CARD", acc="ARO:3000718"),
        _res("paper", "Efflux review", True, pmid="12345"),
        _res("edge", "weak mention", False),  # dropped — not grounded
    ]
    ans = build_answer("how does MarR drive efflux", "computational", results)
    assert ans["refused"] is False
    assert len(ans["claims"]) == 2  # the ungrounded one is excluded
    assert all(c["grounded"] for c in ans["claims"])
    assert ans["intent"] == "mechanism"
    # computational persona gets the provenance caveat
    assert any("provenance" in c.lower() for c in ans["caveats"])


def test_physician_gets_treatment_caveat():
    results = [_res("edge", "meropenem resensitizes", True, relation="sensitizes_to", conf=0.8,
                    pmid="32335276")]
    ans = build_answer("what should I switch to after meropenem", "physician", results)
    assert any("not a treatment recommendation" in c.lower() for c in ans["caveats"])


def test_citation_label():
    assert citation_label({"pmid": "999"}) == "PMID 999"
    assert citation_label({"db": "CARD", "acc": "ARO:1"}) == "CARD:ARO:1"
    assert citation_label({}) is None
