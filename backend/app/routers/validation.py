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
from app.ingestion.domains import DEFAULT_ORGANISM
from app.graph_shaping import pubmed_url, reference_url
from app.ingestion.validation import adjudicate, evaluate, load_benchmark, retrodict

router = APIRouter(prefix="/api/validation", tags=["validation"])

_DEFAULT_ORGANISM = DEFAULT_ORGANISM

# LEFT JOIN papers so each edge carries the publication year of its provenance paper —
# the time axis the retrodiction split runs on. Reference-DB-only edges have year NULL.
_EDGES_SQL = """
    SELECT g.locus_tag AS locus, e.relation, e.target_literal AS target, e.grounded,
           e.provenance_pmid, e.provenance_db, e.provenance_acc, p.year AS year
    FROM evidence_edges e
    JOIN genes g ON g.id = e.source_id
    LEFT JOIN papers p ON p.pmid = e.provenance_pmid
    WHERE e.source_type = 'gene' AND g.organism = :organism
"""


async def _fetch_edges(session: AsyncSession, organism: str) -> list[dict]:
    rows = (
        await session.execute(text(_EDGES_SQL), {"organism": organism})
    ).mappings().all()
    return [
        {
            "locus": r["locus"],
            "relation": r["relation"],
            "target": r["target"],
            "grounded": bool(r["grounded"]),
            "year": r["year"],
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


@router.get("")
async def validation(
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Run the grounded graph against the committed public ground-truth controls."""
    edges = await _fetch_edges(session, organism)
    benchmark = load_benchmark()
    if organism:
        benchmark = {**benchmark, "organism": organism}
    return evaluate(benchmark, edges).model_dump()


@router.get("/retrodiction")
async def retrodiction(
    cutoff: int = 2019,
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Time-split foresight: freeze evidence at ``cutoff`` and measure how many
    later-confirmed relationships the pre-cutoff graph already pointed at.

    e.g. ?cutoff=2019 → AraC/MarA was grounded as an AcrAB-TolC multidrug-efflux driver
    by 2013, so the pre-2020 graph anticipates the 2020 tigecycline-resistance paper it
    never saw. No false control is ever 'anticipated' (foresight without fabrication).
    """
    edges = await _fetch_edges(session, organism)
    benchmark = load_benchmark()
    if organism:
        benchmark = {**benchmark, "organism": organism}
    return retrodict(benchmark, edges, cutoff)


@router.get("/redteam")
async def redteam(
    gene: str,
    target: str,
    relation: str | None = None,
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Adjudicate a claim a judge types in, live, against the grounded graph.

    e.g. ?gene=MarR&target=vancomycin → 'refused' (no grounded evidence);
         ?gene=MarR&target=ciprofloxacin → 'supported' (cited grounded edge).
    The claim is never accepted on faith — only grounded evidence supports it.
    """
    edges = await _fetch_edges(session, organism)
    return adjudicate(gene, target, edges, relation=relation)
