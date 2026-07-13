"""Achilles MCP tool shapers — pure checks (no network, no mcp package needed).

Confirms each tool reduces an API response to a compact, CITED result, and preserves the
non-negotiable: an ungrounded claim comes back refused; nothing is fabricated.
"""

from __future__ import annotations

from mcp_server.tools import (
    shape_ask,
    shape_bridge,
    shape_redteam,
    shape_targets,
    shape_validation,
)


def test_ask_grounded_keeps_only_cited_claims():
    d = {
        "refused": False,
        "deterministic_summary": "8 grounded claims…",
        "answer": {"summary": "MarR represses marRAB [1].", "citations": ["PMID 1"]},
        "claims": [
            {"title": "MarR implicates efflux", "citation": "PMID 41383968"},
            {"title": "uncited", "citation": None},
        ],
        "caveats": ["research evidence"],
    }
    out = shape_ask(d)
    assert out["grounded"] is True and out["source"] == "llm"
    assert out["answer"].startswith("MarR")
    assert len(out["claims"]) == 1 and out["claims"][0]["cite"] == "PMID 41383968"


def test_ask_refused_is_honest():
    out = shape_ask({"refused": True, "deterministic_summary": "No grounded evidence…"})
    assert out["grounded"] is False and out["claims"] == []


def test_ground_claim_verdicts():
    supported = shape_redteam({"verdict": "supported", "grounded": True, "reason": "ok",
                               "provenance": {"acc": "ARO:3003378"}})
    assert supported["verdict"] == "supported" and supported["citation"] == "ARO:3003378"
    refused = shape_redteam({"verdict": "refused", "grounded": False, "reason": "no evidence",
                             "provenance": {}})
    assert refused["verdict"] == "refused" and refused["citation"] is None


def test_targets_sorted_and_trimmed():
    d = {"targets": [
        {"name": "A", "locus_tag": "L1", "rank_score": 0.3, "evidence_counts": {"grounded": 2},
         "tractability": {"bucket": "novel"}},
        {"name": "B", "locus_tag": "L2", "rank_score": 0.9, "evidence_counts": {"grounded": 9},
         "tractability": {"bucket": "precedented"}},
    ]}
    out = shape_targets(d, limit=1)
    assert len(out) == 1 and out[0]["gene"] == "B" and out[0]["rank_score"] == 0.9


def test_validation_summary():
    out = shape_validation({"metrics": {"recovered": 12, "positives": 12, "refused": 17,
                                        "negatives": 17, "fabricated": 0, "clean": True}})
    assert out["recovered"] == "12/12" and out["adversarial_refused"] == "17/17"
    assert out["fabricated"] == 0 and out["controls"] == 29 and out["clean"] is True


def test_bridge_shape_and_not_found():
    ok = shape_bridge({
        "found": True, "gene": {"name": "MarR"},
        "research": {"mechanism": ["efflux"]},
        "clinic": {"drives_resistance_to": ["ciprofloxacin"],
                   "cited_cycle": {"cycle": ["meropenem", "SXT"]},
                   "caveats": ["not medical advice"]},
        "handoff": "same finding, both lenses",
    })
    assert ok["found"] and ok["drives_resistance_to"] == ["ciprofloxacin"]
    assert ok["cited_cycle"] == ["meropenem", "SXT"]
    assert shape_bridge({"found": False, "reason": "unknown"})["found"] is False
