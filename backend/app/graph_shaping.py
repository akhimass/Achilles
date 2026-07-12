"""Pure view-model transforms for the graph endpoints.

Kept free of DB / driver imports so the shaping logic is unit-testable on its own
(the router in `routers/graph.py` runs the SQL and hands rows to these functions).
"""

from __future__ import annotations

# Human verb for each relation, used to compose the auditable claim sentence.
_RELATION_VERB = {
    "confers_resistance": "confers resistance to",
    "sensitizes_to": "sensitizes to",
    "is_target_of": "is targeted by",
    "implicates": "implicates",
    "reverts_with": "reverts with",
}


def claim_sentence(subject: str | None, relation: str | None, target: str | None) -> str:
    """Compose the extracted claim as a short sentence (deterministic)."""
    subj = subject or "This gene"
    verb = _RELATION_VERB.get(relation or "", (relation or "relates to").replace("_", " "))
    obj = target or "its mechanism"
    return f"{subj} {verb} {obj}"


def build_edge_trace(
    *,
    claim: str,
    evidence_span: str | None,
    pmid: str | None,
    pubmed_url_: str | None,
    grounded: bool,
    db: str | None,
    acc: str | None,
    ref_url: str | None,
    grounding_reason: str | None,
    confidence: float,
    extracted_by: str | None,
) -> list[dict]:
    """The ordered provenance chain for one edge, marking each step's actor.

    `actor` is ``"llm"`` (the claim was extracted from text by the model) or
    ``"deterministic"`` (grounding decision + confidence gate are plain Python rules).
    This is the seam the whole product turns on: the model reads text into a typed
    claim; deterministic rules decide whether it becomes a grounded edge and never
    invent the number. Rendering this chain is the direct answer to "shell over an LLM".
    """
    steps: list[dict] = [
        {
            "step": "extracted",
            "actor": "llm",
            "label": "Claim extracted from the abstract",
            "detail": (f"“{evidence_span}”" if evidence_span else claim),
            "source": f"PMID {pmid}" if pmid else None,
            "url": pubmed_url_,
            "by": extracted_by,
        }
    ]
    if grounded and acc:
        steps.append(
            {
                "step": "grounded",
                "actor": "deterministic",
                "label": "Corroborated against a reference database",
                "detail": grounding_reason or "A reference-DB entry supports the claim.",
                "source": f"{db} {acc}" if db else acc,
                "url": ref_url,
                "by": None,
            }
        )
    else:
        steps.append(
            {
                "step": "not_grounded",
                "actor": "deterministic",
                "label": "Not corroborated by a reference DB (abstract-only)",
                "detail": grounding_reason
                or "No reference-DB entry corroborates this yet; shown as weaker evidence.",
                "source": None,
                "url": None,
                "by": None,
            }
        )
    steps.append(
        {
            "step": "scored",
            "actor": "deterministic",
            "label": "Confidence + inclusion gate",
            "detail": (
                f"Confidence {confidence:.2f}; kept as "
                f"{'grounded' if grounded else 'abstract-only'} evidence. "
                "The score is computed, never narrated."
            ),
            "source": None,
            "url": None,
            "by": None,
        }
    )
    return steps


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
        target = r.get("target_literal") or (str(r["target_id"]) if r.get("target_id") else None)
        conf = float(r["confidence"])
        grounded = bool(r["grounded"])
        p_url = pubmed_url(pmid)
        r_url = reference_url(db, acc)
        claim = claim_sentence(meta.get("subject"), r["relation"], target)
        edges.append(
            {
                "id": str(r["id"]) if r.get("id") else None,
                "relation": r["relation"],
                "target": target,
                "target_type": r.get("target_type"),
                "confidence": conf,
                "grounded": grounded,
                "subject": meta.get("subject"),
                "object_kind": meta.get("object_kind"),
                "evidence_span": meta.get("evidence_span"),
                "claim": claim,
                "extracted_by": r.get("extracted_by"),
                "grounding_reason": meta.get("verdict_reason"),
                "provenance": {
                    "pmid": pmid,
                    "pubmed_url": p_url,
                    "db": db,
                    "acc": acc,
                    "ref_url": r_url,
                    "paper_title": r.get("paper_title"),
                    "paper_year": r.get("paper_year"),
                },
                "trace": build_edge_trace(
                    claim=claim,
                    evidence_span=meta.get("evidence_span"),
                    pmid=pmid,
                    pubmed_url_=p_url,
                    grounded=grounded,
                    db=db,
                    acc=acc,
                    ref_url=r_url,
                    grounding_reason=meta.get("verdict_reason"),
                    confidence=conf,
                    extracted_by=r.get("extracted_by"),
                ),
            }
        )
    edges.sort(key=lambda e: (not e["grounded"], -e["confidence"]))
    grounded = sum(1 for e in edges if e["grounded"])
    return {
        "gene": gene,
        "edges": edges,
        "counts": {"total": len(edges), "grounded": grounded},
    }
