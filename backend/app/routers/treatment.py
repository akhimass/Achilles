"""Treatment endpoint: deterministic antibiotic cycle + optional LLM narration.

The reciprocal-CS pairs come from `collateral_sensitivity` (seeded deterministically
from the per-lineage resistance/sensitivity record); `ingestion/collateral.propose_cycle`
computes the cycle. The LLM (`ai/treatment.narrate_cycle`) only explains it and is
strictly opt-in (`narrate=true`) — it never designs or reorders the cycle. Always a
research hypothesis, never a treatment recommendation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.collateral import CollateralPair, propose_cycle
from app.treatment_shaping import shape_cycle

router = APIRouter(prefix="/api/treatment", tags=["treatment"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_CS_SQL = """
    SELECT organism, drug_a, drug_b, reciprocal, strength, n_lineages, metadata
    FROM collateral_sensitivity
    WHERE organism = :organism
    ORDER BY reciprocal DESC, n_lineages DESC NULLS LAST, drug_a, drug_b
"""


@router.get("/cycle")
async def cycle(
    organism: str = _DEFAULT_ORGANISM,
    narrate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Propose an antibiotic cycle for an organism, with cited (opt-in) narration.

    The cycle is computed from the reciprocal collateral-sensitivity graph; the LLM
    only narrates when `narrate=true`. Degrades to an explicit empty state when no
    collateral data is seeded (e.g. the public path without BurkData).
    """
    rows = (
        await session.execute(text(_CS_SQL), {"organism": organism})
    ).mappings().all()

    pairs = [
        CollateralPair(
            organism=r["organism"],
            drug_a=r["drug_a"],
            drug_b=r["drug_b"],
            reciprocal=bool(r["reciprocal"]),
            strength=r["strength"],
            n_lineages=r["n_lineages"],
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]

    proposed = propose_cycle(pairs)

    narrative: dict | None = None
    if narrate and proposed:
        narrative = await _narrate(organism, pairs, proposed)

    return shape_cycle(organism, proposed, pairs, narrative=narrative)


async def _narrate(organism: str, pairs: list[CollateralPair], proposed: list[str]) -> dict | None:
    """Best-effort LLM narration; returns None if unavailable (no key / network).

    Never raises into the request and never changes the cycle. The reciprocal pairs and
    the ordered cycle are passed in already computed.
    """
    from app.ai.treatment import narrate_cycle

    rcs = [p for p in pairs if p.reciprocal]
    evidence = (
        "Collateral-sensitivity structure computed from per-lineage resistance/"
        "sensitivity transitions (BurkholderIa multivorans experimental evolution). "
        f"{len(rcs)} reciprocal pairs support the cycle."
    )
    try:
        result = await narrate_cycle(
            organism=organism, rcs_pairs=rcs, cycle=proposed, evidence=evidence
        )
        if result:
            return {
                "summary": result.summary,
                "caveats": list(result.caveats or []),
                "citations": list(result.citations or []),
            }
    except Exception:
        return None
    return None
