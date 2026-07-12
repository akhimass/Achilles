"""Treatment endpoint: deterministic cycle + LLM narration."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/api/treatment", tags=["treatment"])


@router.get("/cycle")
async def cycle(organism: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Propose an antibiotic cycle for an organism, with cited narration.

    Phase 4 TODO: read collateral_sensitivity -> ingestion.collateral.propose_cycle
    (deterministic) -> ai.treatment.narrate_cycle for the explanation. The cycle is
    computed; the LLM only explains it.
    """
    _ = session, organism
    return {"cycle": [], "narrative": None, "todo": "Phase 4: cycle + narration"}
