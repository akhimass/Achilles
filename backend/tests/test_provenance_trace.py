"""Slice 2 tests: edge-level provenance tracing. No DB, no network, no LLM.

Locks the seam that answers "shell over an LLM": the claim was LLM-extracted; grounding
and the confidence gate are deterministic. Every edge exposes a traceable chain.
"""

from __future__ import annotations

from app.graph_shaping import build_edge_trace, claim_sentence, shape_evidence
from app.targets_shaping import shape_evidence_edge


def test_claim_sentence_composes_relation_verb():
    assert claim_sentence("MarR", "confers_resistance", "ciprofloxacin") == (
        "MarR confers resistance to ciprofloxacin"
    )
    assert claim_sentence(None, "implicates", None) == "This gene implicates its mechanism"


def test_trace_grounded_edge_marks_actors():
    steps = build_edge_trace(
        claim="MarR confers resistance to ciprofloxacin",
        evidence_span="MarR mutations confer ciprofloxacin resistance",
        pmid="222", pubmed_url_="https://pubmed.ncbi.nlm.nih.gov/222/",
        grounded=True, db="CARD", acc="ARO:3003378",
        ref_url="https://card.mcmaster.ca/aro/3003378",
        grounding_reason="ARO entry corroborates MarR→fluoroquinolone resistance.",
        confidence=0.95, extracted_by="ai/extraction.py@claude-sonnet-5",
    )
    assert [s["step"] for s in steps] == ["extracted", "grounded", "scored"]
    assert steps[0]["actor"] == "llm" and steps[0]["by"].endswith("claude-sonnet-5")
    assert steps[0]["source"] == "PMID 222" and steps[0]["url"].endswith("/222/")
    assert steps[1]["actor"] == "deterministic" and steps[1]["source"] == "CARD ARO:3003378"
    assert steps[2]["actor"] == "deterministic" and "0.95" in steps[2]["detail"]


def test_trace_ungrounded_edge_is_abstract_only():
    steps = build_edge_trace(
        claim="recA implicates SOS response", evidence_span="the SOS response",
        pmid="111", pubmed_url_="https://pubmed.ncbi.nlm.nih.gov/111/",
        grounded=False, db=None, acc=None, ref_url=None,
        grounding_reason=None, confidence=0.3, extracted_by="ai/extraction.py@claude-sonnet-5",
    )
    assert [s["step"] for s in steps] == ["extracted", "not_grounded", "scored"]
    assert steps[1]["actor"] == "deterministic" and steps[1]["source"] is None
    assert "abstract-only" in steps[2]["detail"]


def _row(**kw) -> dict:
    base = dict(id="e1", relation="confers_resistance", target_type="drug", target_id=None,
                target_literal="ciprofloxacin", confidence=0.95, grounded=True,
                provenance_pmid="222", provenance_db="CARD", provenance_acc="ARO:3003378",
                extracted_by="ai/extraction.py@claude-sonnet-5",
                metadata={"subject": "MarR", "object_kind": "drug",
                          "evidence_span": "MarR mutations confer ciprofloxacin resistance",
                          "verdict_reason": "ARO corroborates."},
                paper_title="MarR and efflux", paper_year=2021)
    base.update(kw)
    return base


def test_shape_evidence_adds_claim_and_trace():
    out = shape_evidence({"locus_tag": "A8H40_RS07590", "symbol": "MarR"}, [_row()])
    e = out["edges"][0]
    assert e["claim"] == "MarR confers resistance to ciprofloxacin"
    assert e["extracted_by"].endswith("claude-sonnet-5")
    assert e["object_kind"] == "drug"
    assert e["grounding_reason"] == "ARO corroborates."
    assert [s["step"] for s in e["trace"]] == ["extracted", "grounded", "scored"]
    # The grounded, cited chain is intact end to end.
    assert e["trace"][0]["url"].endswith("/222/")
    assert e["trace"][1]["url"].endswith("/aro/3003378")


def test_targets_and_graph_edge_shapes_agree_on_trace():
    # Both endpoints must expose the same trace contract for one edge.
    g = shape_evidence({"locus_tag": "L"}, [_row()])["edges"][0]
    t = shape_evidence_edge(_row(source_id="g1"))
    assert [s["step"] for s in g["trace"]] == [s["step"] for s in t["trace"]]
    assert g["claim"] == t["claim"] and g["grounding_reason"] == t["grounding_reason"]
