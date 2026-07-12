"""Slice 4 tests: reproducibility export shaping. No DB, no network, no LLM.

Locks that the citable artifact carries the methods header (deterministic pipeline +
public sources + disclaimer), every provenance id, and confidences — in both JSON and
CSV — so "reproducible" is tangible and auditable.
"""

from __future__ import annotations

import csv
import io

from app.export_shaping import build_evidence_export, evidence_export_csv, methods_header
from app.graph_shaping import shape_evidence

_GEN = "2026-07-12T00:00:00+00:00"


def _edge_row(**kw) -> dict:
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


def _ungrounded_row() -> dict:
    return _edge_row(id="e2", relation="implicates", target_type="mechanism",
                     target_literal="SOS response", confidence=0.3, grounded=False,
                     provenance_pmid="111", provenance_db=None, provenance_acc=None,
                     metadata={"subject": "recA", "object_kind": "mechanism"})


def _export() -> dict:
    gene = {"locus_tag": "A8H40_RS07590", "symbol": "MarR", "product": "MarR family regulator"}
    shaped = shape_evidence(gene, [_edge_row(), _ungrounded_row()])
    return build_evidence_export(gene, shaped["edges"], "Burkholderia multivorans", _GEN)


def test_methods_header_names_pipeline_sources_and_disclaimer():
    m = methods_header("Burkholderia multivorans", _GEN)
    assert "PubMLST" in m["public_sources"] and "ChEMBL" in m["public_sources"]
    assert any("no LLM" in s for s in m["deterministic_steps"])
    assert any("extract" in s for s in m["llm_steps"])
    assert "provenance" in m["principle"].lower()
    assert "not clinical" in m["disclaimer"].lower()


def test_build_export_carries_provenance_and_counts():
    exp = _export()
    assert exp["selection"]["locus_tag"] == "A8H40_RS07590"
    assert exp["counts"] == {"edges": 2, "grounded": 1, "abstract_only": 1}
    # Grounded edge sorts first (shape_evidence) and keeps its PMID + accession.
    g = exp["edges"][0]
    assert g["pmid"] == "222" and g["reference_acc"] == "ARO:3003378"
    assert g["confidence"] == 0.95 and g["grounded"] is True
    assert g["claim"] == "MarR confers resistance to ciprofloxacin"
    # Abstract-only edge keeps its PMID and has no reference accession.
    u = exp["edges"][1]
    assert u["pmid"] == "111" and u["reference_acc"] is None and u["grounded"] is False


def test_csv_has_methods_header_and_one_row_per_edge():
    csv_text = evidence_export_csv(_export())
    assert csv_text.startswith("# achilles-evidence-export/1")
    assert "# public_sources:" in csv_text and "PubMLST" in csv_text
    assert "# disclaimer:" in csv_text
    # Parse the data rows (skip comment lines) and check provenance columns survive.
    data_lines = [ln for ln in csv_text.splitlines() if not ln.startswith("#")]
    rows = list(csv.DictReader(io.StringIO("\n".join(data_lines))))
    assert len(rows) == 2
    assert rows[0]["pmid"] == "222" and rows[0]["reference_acc"] == "ARO:3003378"
    assert rows[0]["confidence"] == "0.95"
    assert set(["subject", "relation", "object", "confidence", "grounded", "pmid",
                "reference_acc", "extracted_by"]).issubset(rows[0].keys())


def test_export_of_gene_with_no_edges_is_empty_but_valid():
    exp = build_evidence_export({"locus_tag": "X", "symbol": None, "product": None}, [],
                                "Burkholderia multivorans", _GEN)
    assert exp["counts"] == {"edges": 0, "grounded": 0, "abstract_only": 0}
    assert exp["methods"]["tool"].startswith("achilles-evidence-export")
    assert evidence_export_csv(exp).count("\n") >= 7  # header comments + column row
