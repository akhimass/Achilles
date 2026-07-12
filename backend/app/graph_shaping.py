"""Pure view-model transforms for the graph endpoints.

Kept free of DB / driver imports so the shaping logic is unit-testable on its own
(the router in `routers/graph.py` runs the SQL and hands rows to these functions).
"""

from __future__ import annotations


def shape_lineage(rows: list[dict]) -> dict:
    """Shape strain rows into the {nodes, edges} LineageGraph the frontend renders.

    Deterministic. `flipper_count` colors each node; an edge is emitted only when a
    row's parent is itself in the node set, so a subtree slice never dangles. Node id
    and parent_id are stringified UUIDs to match the TS `LineageNode` contract.
    """
    node_ids = {str(r["id"]) for r in rows}
    nodes = [
        {
            "id": str(r["id"]),
            "label": r["label"] or str(r["id"]),
            "parent_id": str(r["parent_id"]) if r.get("parent_id") else None,
            "flipper_count": int(r["flipper_count"]),
            "st": r.get("st"),
            "year": r.get("year"),
            "country": r.get("country"),
            "lineage": r.get("lineage"),
            "founder": bool(r["founder"]) if r.get("founder") is not None else None,
        }
        for r in rows
    ]
    edges = [
        {"source": str(r["parent_id"]), "target": str(r["id"])}
        for r in rows
        if r.get("parent_id") and str(r["parent_id"]) in node_ids
    ]
    return {"nodes": nodes, "edges": edges}


def pubmed_url(pmid: str | None) -> str | None:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None


def reference_url(db: str | None, acc: str | None) -> str | None:
    """Resolve a reference-DB accession to its public page."""
    if not acc:
        return None
    d = (db or "").lower()
    if d == "card" or acc.upper().startswith("ARO"):
        return f"https://card.mcmaster.ca/aro/{acc.split(':')[-1]}"
    if d == "uniprot":
        return f"https://www.uniprot.org/uniprotkb/{acc}/entry"
    return None


def shape_evidence(gene: dict, rows: list[dict]) -> dict:
    """Shape evidence-edge rows into the subgraph the EvidencePanel renders.

    Pure: the router runs SQL and hands rows here. Each edge exposes its relation,
    target, confidence, grounded flag, and resolved provenance links. Grounded edges
    (PMID + reference accession) sort first, then by confidence.
    """
    edges = []
    for r in rows:
        meta = r.get("metadata") or {}
        pmid = r.get("provenance_pmid")
        acc = r.get("provenance_acc")
        db = r.get("provenance_db")
        edges.append(
            {
                "id": str(r["id"]) if r.get("id") else None,
                "relation": r["relation"],
                "target": r.get("target_literal") or (str(r["target_id"]) if r.get("target_id") else None),
                "target_type": r.get("target_type"),
                "confidence": float(r["confidence"]),
                "grounded": bool(r["grounded"]),
                "subject": meta.get("subject"),
                "evidence_span": meta.get("evidence_span"),
                "provenance": {
                    "pmid": pmid,
                    "pubmed_url": pubmed_url(pmid),
                    "db": db,
                    "acc": acc,
                    "ref_url": reference_url(db, acc),
                    "paper_title": r.get("paper_title"),
                    "paper_year": r.get("paper_year"),
                },
            }
        )
    edges.sort(key=lambda e: (not e["grounded"], -e["confidence"]))
    grounded = sum(1 for e in edges if e["grounded"])
    return {
        "gene": gene,
        "edges": edges,
        "counts": {"total": len(edges), "grounded": grounded},
    }
