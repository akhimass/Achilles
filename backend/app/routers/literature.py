"""Literature endpoints: ingest a scoped corpus and extract grounded edges.

The demo reads a committed offline corpus (see ingestion/seed_literature.py). This
LIVE path lets a user fetch *new* literature for a selected gene on demand — it hits
Europe PMC + the LLM + reference DBs, then upserts the surviving grounded/ungrounded
edges. It is not required for the offline demo.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.domains import DEFAULT_ORGANISM
from app.ingestion.seed_literature import upsert_papers_and_edges

router = APIRouter(prefix="/api/literature", tags=["literature"])


@router.post("/ingest")
async def ingest(
    locus: str,
    organism: str = DEFAULT_ORGANISM,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Fetch fresh literature for a gene, extract + ground claims, upsert edges."""
    grow = (
        await session.execute(
            text(
                "SELECT locus_tag, name, product FROM genes WHERE organism = :o AND locus_tag = :l"
            ),
            {"o": organism, "l": locus},
        )
    ).mappings().first()
    if grow is None:
        return {"ingested": 0, "edges": 0, "error": f"unknown gene {locus}"}

    # Import the pipeline lazily — it pulls in the AI/network layer.
    from app.sources.make_literature_snapshot import harvest_gene

    symbol = grow["name"] or grow["product"] or locus
    # Constrain claims to the gene family where we have a symbol; else trust the query.
    topic = re.escape(grow["name"].lower()) if grow["name"] else r"."
    entry = {
        "locus": locus,
        "symbol": symbol,
        "ground_symbol": grow["name"] or symbol,
        "queries": [f"{symbol} {organism} antibiotic resistance efflux"],
        "topic": topic,
    }
    papers, edges = await harvest_gene(entry, organism, per_query_limit=limit)
    summary = await upsert_papers_and_edges(
        [p.model_dump(mode="json") for p in papers.values()],
        [e for e, _ in edges],
    )
    return {"ingested": summary["papers"], "edges": summary["edges"], "grounded": summary["grounded"]}
