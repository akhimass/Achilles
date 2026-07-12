"""Validation endpoint — the engine proves itself against public ground truth.

`GET /api/validation` runs the live grounded graph against independent public controls
and returns a deterministic report: how many established relationships it RECOVERS (each
cited) and how many false controls it FABRICATES (must be 0). This is the "prove-it"
property a retrieval/search tool can't produce — precision (no invention) and recall
(recovers known biology), computed, not asserted.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.graph_shaping import pubmed_url, reference_url
from app.ingestion.validation import evaluate, load_benchmark

router = APIRouter(prefix="/api/validation", tags=["validation"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_EDGES_SQL = """
    SELECT g.locus_tag AS locus, e.relation, e.target_literal AS target, e.grounded,
           e.provenance_pmid, e.provenance_db, e.provenance_acc
    FROM evidence_edges e
    JOIN genes g ON g.id = e.source_id
    WHERE e.source_type = 'gene' AND g.organism = :organism
"""


@router.get("")
async def validation(
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run the grounded graph against the committed public ground-truth controls."""
    rows = (
        await session.execute(text(_EDGES_SQL), {"organism": organism})
    ).mappings().all()

    edges = [
        {
            "locus": r["locus"],
            "relation": r["relation"],
            "target": r["target"],
            "grounded": bool(r["grounded"]),
            "provenance": {
                "pmid": r["provenance_pmid"],
                "pubmed_url": pubmed_url(r["provenance_pmid"]),
                "db": r["provenance_db"],
                "acc": r["provenance_acc"],
                "ref_url": reference_url(r["provenance_db"], r["provenance_acc"]),
            },
        }
        for r in rows
    ]

    benchmark = load_benchmark()
    if organism:
        benchmark = {**benchmark, "organism": organism}
    return evaluate(benchmark, edges).model_dump()
