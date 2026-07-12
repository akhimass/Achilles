"""Phase 2 tests: Europe PMC mapping, the grounding decision logic, evidence-subgraph
shaping, and corpus edge rebuild. All deterministic — no network, no LLM.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.ai.extraction import ExtractedClaim
from app.ai.grounding import DROP_FLOOR, GroundingVerdict, decide_edge
from app.graph_shaping import pubmed_url, reference_url, shape_evidence
from app.ingestion.seed import _burk_gene_id
from app.ingestion.seed_literature import rebuild_edges
from app.sources.europepmc import hit_to_paper

GENE_ID = _burk_gene_id("A8H40_RS07590")


def _claim(**kw) -> ExtractedClaim:
    base = dict(
        subject="MarR",
        relation="confers_resistance",
        object="ciprofloxacin",
        object_kind="drug",
        evidence_span="MarR mutations confer ciprofloxacin resistance",
        confidence=0.8,
    )
    base.update(kw)
    return ExtractedClaim(**base)


def _supported() -> GroundingVerdict:
    return GroundingVerdict(
        supported=True, provenance_db="CARD", provenance_acc="ARO:3003378",
        adjusted_confidence=0.9, reason="ARO corroborates",
    )


def _unsupported() -> GroundingVerdict:
    return GroundingVerdict(supported=False, adjusted_confidence=0.0, reason="no reference hit")


# ─── Europe PMC mapping ──────────────────────────────────────────────────────


def test_hit_to_paper_maps_core_fields():
    p = hit_to_paper(
        {"pmid": "12345", "title": "MarR and efflux.", "abstractText": "MarR regulates efflux.",
         "pubYear": "2019", "doi": "10.1/x"}
    )
    assert p is not None
    assert p.pmid == "12345" and p.year == 2019 and p.doi == "10.1/x"
    assert p.title == "MarR and efflux"  # trailing period trimmed
    assert p.source == "europepmc"


def test_hit_to_paper_drops_without_pmid_or_abstract():
    assert hit_to_paper({"title": "x", "abstractText": "y"}) is None  # no pmid
    assert hit_to_paper({"pmid": "1", "title": "x"}) is None  # no abstract


# ─── Grounding decision (the credibility gate) ───────────────────────────────


def test_supported_claim_becomes_grounded_edge_with_both_provenances():
    e = decide_edge(_claim(), _supported(), gene_id=GENE_ID, gene_symbol="MarR",
                    gene_locus="A8H40_RS07590", paper_pmid="777", extracted_by="test")
    assert e is not None
    assert e.grounded is True
    assert e.provenance_pmid == "777"  # PMID
    assert e.provenance_db == "CARD" and e.provenance_acc == "ARO:3003378"  # reference
    assert e.confidence >= 0.5  # grounded edges are visibly strong
    assert e.relation.value == "confers_resistance"
    assert e.target_literal == "ciprofloxacin"


def test_abstract_only_claim_is_pmid_only_and_weaker():
    e = decide_edge(_claim(confidence=0.8), _unsupported(), gene_id=GENE_ID, gene_symbol="MarR",
                    gene_locus="A8H40_RS07590", paper_pmid="777", extracted_by="test")
    assert e is not None
    assert e.grounded is False
    assert e.provenance_pmid == "777"
    assert e.provenance_acc is None and e.provenance_db is None
    assert e.confidence < 0.5  # clearly weaker than grounded


def test_weak_unsupported_claim_is_dropped():
    assert (
        decide_edge(_claim(confidence=DROP_FLOOR - 0.05), _unsupported(), gene_id=GENE_ID,
                    gene_symbol="MarR", gene_locus="A8H40_RS07590", paper_pmid="777",
                    extracted_by="test")
        is None
    )


def test_invalid_relation_and_missing_pmid_are_dropped():
    assert (
        decide_edge(_claim(relation="not_a_relation"), _supported(), gene_id=GENE_ID,
                    gene_symbol="MarR", gene_locus="A8H40_RS07590", paper_pmid="777",
                    extracted_by="test")
        is None
    )
    assert (
        decide_edge(_claim(), _supported(), gene_id=GENE_ID, gene_symbol="MarR",
                    gene_locus="A8H40_RS07590", paper_pmid=None, extracted_by="test")
        is None
    )


# ─── Provenance URLs ─────────────────────────────────────────────────────────


def test_provenance_urls():
    assert pubmed_url("777") == "https://pubmed.ncbi.nlm.nih.gov/777/"
    assert pubmed_url(None) is None
    assert reference_url("CARD", "ARO:3003378") == "https://card.mcmaster.ca/aro/3003378"
    assert reference_url("UniProt", "P0A9Y6") == "https://www.uniprot.org/uniprotkb/P0A9Y6/entry"
    assert reference_url(None, None) is None


# ─── Evidence subgraph shaping ───────────────────────────────────────────────


def test_shape_evidence_sorts_grounded_first_and_resolves_links():
    rows = [
        {"id": "u", "relation": "implicates", "target_type": "mechanism", "target_id": None,
         "target_literal": "SOS response", "confidence": 0.3, "grounded": False,
         "provenance_pmid": "111", "provenance_db": None, "provenance_acc": None,
         "metadata": {"subject": "recA", "evidence_span": "..."}, "paper_title": "T1", "paper_year": 2020},
        {"id": "g", "relation": "confers_resistance", "target_type": "drug", "target_id": None,
         "target_literal": "ciprofloxacin", "confidence": 0.95, "grounded": True,
         "provenance_pmid": "222", "provenance_db": "CARD", "provenance_acc": "ARO:3003378",
         "metadata": {"subject": "MarR", "evidence_span": "..."}, "paper_title": "T2", "paper_year": 2021},
    ]
    out = shape_evidence({"locus_tag": "A8H40_RS07590", "symbol": "MarR"}, rows)
    assert out["counts"] == {"total": 2, "grounded": 1}
    assert out["edges"][0]["grounded"] is True  # grounded sorts first
    assert out["edges"][0]["provenance"]["pubmed_url"].endswith("/222/")
    assert out["edges"][0]["provenance"]["ref_url"].endswith("/aro/3003378")
    assert out["edges"][1]["provenance"]["ref_url"] is None


# ─── Corpus edge rebuild (offline seed) ──────────────────────────────────────


def test_rebuild_edges_recomputes_source_and_drops_malformed():
    good = decide_edge(_claim(), _supported(), gene_id=GENE_ID, gene_symbol="MarR",
                       gene_locus="A8H40_RS07590", paper_pmid="777", extracted_by="test")
    good_row = good.model_dump(mode="json")
    good_row["gene_locus"] = "A8H40_RS07590"
    good_row["source_id"] = str(uuid5(NAMESPACE_URL, "wrong"))  # should be recomputed from locus
    malformed = {"gene_locus": "A8H40_RS07590", "relation": "confers_resistance",
                 "target_literal": "x"}  # no provenance -> validator rejects

    edges = rebuild_edges({"edges": [good_row, malformed]})
    assert len(edges) == 1
    assert edges[0].source_id == GENE_ID  # recomputed from public locus
    assert edges[0].provenance_pmid == "777"
