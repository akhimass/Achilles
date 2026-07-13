"""Structure endpoint — AlphaFold (Tamarind) / RCSB 3D structure for a flipper gene.

The AI/ML beat: a gene the lineage flags as a flipper resolves to its protein and a
predicted structure with per-residue confidence, which the frontend renders in 3D.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tamarind import get_structure
from app.db import get_session
from app.ingestion.domains import DEFAULT_ORGANISM

router = APIRouter(prefix="/api/structure", tags=["structure"])


@router.get("")
async def structure(
    locus: str,
    organism: str = DEFAULT_ORGANISM,
    submit: bool = True,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Resolve a 3D structure for a gene by locus tag."""
    row = (
        await session.execute(
            text(
                """
                SELECT locus_tag, name, product, metadata->>'wp' AS wp
                FROM genes
                WHERE organism = :organism AND locus_tag = :locus
                """
            ),
            {"organism": organism, "locus": locus},
        )
    ).mappings().first()

    if row is None:
        return {"locus_tag": locus, "status": "unavailable", "source": "unavailable", "pdb": None,
                "note": "Unknown gene."}

    return await get_structure(
        locus_tag=row["locus_tag"],
        wp=row["wp"],
        name=row["name"],
        product=row["product"],
        submit=submit,
    )
