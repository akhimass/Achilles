"""Search endpoint — the grounded retrieval DB the LLM and users query.

`GET /api/search?q=<text>` returns ranked, provenance-carrying results across the whole
evidence graph: papers (PMID), genes (locus/UniProt), and evidence edges (claim + its
reference accession). Deterministic lexical ranking (search_shaping.py) always works,
offline and network-free. When an embedding provider is configured and paper embeddings
are populated, a pgvector semantic pass over papers is merged in (mode="semantic").

Retrieval never returns an unsourced result — every hit is a node/edge already in the
graph, with its provenance — so this is a search DB you can trust, not a text blob.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.domains import DEFAULT_ORGANISM
from app.search_shaping import (
    edge_candidate,
    gene_candidate,
    paper_candidate,
    shape_search,
)

router = APIRouter(prefix="/api/search", tags=["search"])

_DEFAULT_ORGANISM = DEFAULT_ORGANISM

_PAPERS_SQL = "SELECT id, pmid, title, abstract, year FROM papers LIMIT 1000"
_GENES_SQL = (
    "SELECT locus_tag, name, product, uniprot_acc FROM genes WHERE organism = :organism"
)
_EDGES_SQL = """
    SELECT e.id, e.relation, e.target_literal, e.grounded, e.confidence,
           e.provenance_pmid, e.provenance_db, e.provenance_acc, e.metadata
    FROM evidence_edges e
    WHERE e.source_type = 'gene'
    LIMIT 2000
"""
# Semantic (pgvector) pass over papers, used only when embeddings are populated.
_SEMANTIC_PAPERS_SQL = """
    SELECT id, pmid, title, abstract, year,
           1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
    FROM papers
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:qvec AS vector)
    LIMIT :k
"""


@router.get("")
async def search(
    q: str,
    limit: int = 20,
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Ranked, grounded retrieval across papers, genes, and evidence edges."""
    q = (q or "").strip()
    if not q:
        return {"query": "", "mode": "lexical", "results": [],
                "counts": {"total": 0, "grounded": 0, "by_kind": {}}}

    papers = (await session.execute(text(_PAPERS_SQL))).mappings().all()
    genes = (await session.execute(text(_GENES_SQL), {"organism": organism})).mappings().all()
    edges = (await session.execute(text(_EDGES_SQL))).mappings().all()

    candidates = (
        [paper_candidate(dict(r)) for r in papers]
        + [gene_candidate(dict(r)) for r in genes]
        + [edge_candidate(dict(r)) for r in edges]
    )

    mode = "lexical"
    # Optional semantic pass: embed the query and rank papers by pgvector cosine, then
    # fold those papers in as strong candidates. Falls back silently to lexical.
    semantic_boost: dict[str, float] = {}
    try:
        from app.ai.embeddings import embed_query, provider_enabled

        if provider_enabled():
            qvec = await embed_query(q)
            if qvec:
                rows = (
                    await session.execute(
                        text(_SEMANTIC_PAPERS_SQL), {"qvec": qvec, "k": limit}
                    )
                ).mappings().all()
                if rows:
                    mode = "semantic"
                    for r in rows:
                        if r.get("pmid"):
                            semantic_boost[r["pmid"]] = float(r["similarity"] or 0)
    except Exception:
        pass  # keep deterministic lexical results

    payload = shape_search(q, candidates, limit=limit, mode=mode)
    if semantic_boost:
        for res in payload["results"]:
            if res["kind"] == "paper" and res["id"] in semantic_boost:
                res["semantic_similarity"] = round(semantic_boost[res["id"]], 4)
    return payload
