"""Pure shaping for the reproducibility export — a citable evidence-graph artifact.

Makes "reproducible" tangible: a judge can download the receipts for a selection — the
edges, their confidences, and every provenance id (PMIDs + reference accessions) —
under a short methods header naming the deterministic pipeline and the public sources.

Kept free of DB / network imports so it is unit-testable; the router runs the SQL and
hands already-shaped edges (from `graph_shaping.shape_evidence`) here. Public data only.
"""

from __future__ import annotations

import csv
import io

EXPORT_VERSION = "achilles-evidence-export/1"

# Deterministic vs. LLM, stated in the artifact itself so the export is self-describing.
_DETERMINISTIC_STEPS = [
    "parse / lineage / flipper detection (ingestion, no LLM)",
    "grounding decision + confidence gate (ai/grounding.decide_edge rules)",
    "target rank_score (ingestion/scoring, no LLM)",
    "collateral-sensitivity + cycle (ingestion/collateral, no LLM)",
]
_LLM_STEPS = [
    "extract typed claims from public abstracts (ai/extraction)",
    "narrate computed results with citations (ai/targets, ai/treatment) — never a number",
]
_PUBLIC_SOURCES = [
    "PubMLST", "Europe PMC / PubMed", "CARD (ARO via EBI OLS)", "UniProt",
    "ChEMBL", "NCBI", "AlphaFold (Tamarind Bio)", "RCSB",
]

# Flat column order for CSV / row export (stable, documented).
_EDGE_COLUMNS = [
    "subject", "relation", "object", "object_kind", "claim", "confidence", "grounded",
    "pmid", "pubmed_url", "reference_db", "reference_acc", "reference_url",
    "paper_title", "paper_year", "extracted_by", "grounding_reason",
]


def methods_header(organism: str, generated_at: str) -> dict:
    """Self-describing methods block: the pipeline, the seam, the sources, the caveat."""
    return {
        "tool": EXPORT_VERSION,
        "organism": organism,
        "generated_at": generated_at,
        "principle": (
            "Deterministic core computes every number; the LLM only extracts typed "
            "claims and narrates with citations. Provenance is on every edge — no "
            "ungrounded claim is presented as validated."
        ),
        "deterministic_steps": list(_DETERMINISTIC_STEPS),
        "llm_steps": list(_LLM_STEPS),
        "public_sources": list(_PUBLIC_SOURCES),
        "disclaimer": (
            "Research artifact from public data — not clinical guidance. Cycling "
            "suggestions are hypotheses, not treatment recommendations."
        ),
    }


def _flatten_edge(e: dict) -> dict:
    """One shaped evidence edge → a flat, citable row (provenance ids preserved)."""
    prov = e.get("provenance") or {}
    return {
        "subject": e.get("subject"),
        "relation": e.get("relation"),
        "object": e.get("target"),
        "object_kind": e.get("object_kind"),
        "claim": e.get("claim"),
        "confidence": e.get("confidence"),
        "grounded": e.get("grounded"),
        "pmid": prov.get("pmid"),
        "pubmed_url": prov.get("pubmed_url"),
        "reference_db": prov.get("db"),
        "reference_acc": prov.get("acc"),
        "reference_url": prov.get("ref_url"),
        "paper_title": prov.get("paper_title"),
        "paper_year": prov.get("paper_year"),
        "extracted_by": e.get("extracted_by"),
        "grounding_reason": e.get("grounding_reason"),
    }


def build_evidence_export(gene: dict, edges: list[dict], organism: str, generated_at: str) -> dict:
    """Assemble the citable JSON artifact for a gene's evidence subgraph. Pure."""
    rows = [_flatten_edge(e) for e in edges]
    grounded = sum(1 for r in rows if r["grounded"])
    return {
        "methods": methods_header(organism, generated_at),
        "selection": {
            "kind": "gene",
            "locus_tag": gene.get("locus_tag"),
            "symbol": gene.get("symbol") or gene.get("name"),
            "product": gene.get("product"),
        },
        "columns": list(_EDGE_COLUMNS),
        "edges": rows,
        "counts": {"edges": len(rows), "grounded": grounded, "abstract_only": len(rows) - grounded},
    }


def evidence_export_csv(export: dict) -> str:
    """Serialize the export to CSV: a commented methods header, then one row per edge."""
    buf = io.StringIO()
    m = export["methods"]
    sel = export["selection"]
    buf.write(f"# {m['tool']} — {m['organism']}\n")
    buf.write(f"# selection: gene {sel.get('locus_tag')} ({sel.get('symbol') or ''})\n")
    buf.write(f"# generated_at: {m['generated_at']}\n")
    buf.write(f"# principle: {m['principle']}\n")
    buf.write(f"# public_sources: {', '.join(m['public_sources'])}\n")
    buf.write(f"# disclaimer: {m['disclaimer']}\n")
    writer = csv.DictWriter(buf, fieldnames=_EDGE_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in export["edges"]:
        writer.writerow(row)
    return buf.getvalue()
