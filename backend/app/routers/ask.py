"""Ask endpoint — grounded, persona-aware question answering over the evidence graph.

`GET /api/ask?q=<question>&persona=<researcher|physician|computational>` retrieves
grounded evidence (the same deterministic retrieval as /api/search), builds a cited
answer packet (app/qa.py), and — when `narrate=true` and a model key is configured —
adds a 2-3 sentence LLM synthesis composed ONLY from those claims. If nothing grounded
is retrieved, it refuses. It never answers from outside the graph.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.qa import build_answer, citation_label
from app.search_shaping import edge_candidate, gene_candidate, paper_candidate, rank_results

router = APIRouter(prefix="/api/ask", tags=["ask"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_PAPERS_SQL = "SELECT id, pmid, title, abstract, year FROM papers LIMIT 1000"
_GENES_SQL = "SELECT locus_tag, name, product, uniprot_acc FROM genes WHERE organism = :organism"
_EDGES_SQL = """
    SELECT e.id, e.relation, e.target_literal, e.grounded, e.confidence,
           e.provenance_pmid, e.provenance_db, e.provenance_acc, e.metadata
    FROM evidence_edges e
    WHERE e.source_type = 'gene'
    LIMIT 2000
"""


@router.get("")
async def ask(
    q: str,
    persona: str = "researcher",
    narrate: bool = True,
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Answer a plain-language question strictly from grounded graph evidence."""
    q = (q or "").strip()
    if not q:
        return build_answer("", persona, [])

    papers = (await session.execute(text(_PAPERS_SQL))).mappings().all()
    genes = (await session.execute(text(_GENES_SQL), {"organism": organism})).mappings().all()
    edges = (await session.execute(text(_EDGES_SQL))).mappings().all()

    candidates = (
        [paper_candidate(dict(r)) for r in papers]
        + [gene_candidate(dict(r)) for r in genes]
        + [edge_candidate(dict(r)) for r in edges]
    )
    results = rank_results(q, candidates, limit=12)
    answer = build_answer(q, persona, results)

    # Optional grounded LLM synthesis — phrases the claims, never adds facts.
    if narrate and not answer["refused"]:
        from app.ai.ask import synthesize

        syn = await synthesize(q, answer["persona"], answer["claims"])
        if syn:
            answer["answer"] = {
                "summary": syn.summary,
                "citations": syn.citations,
                "caveats": syn.caveats,
                "refused": syn.refused,
                "source": "llm",
            }
            for c in syn.caveats:
                if c and c not in answer["caveats"]:
                    answer["caveats"].append(c)

    # Attach a stable citation label per claim for the UI.
    for c in answer["claims"]:
        c["citation"] = citation_label(c.get("provenance") or {})
    return answer
