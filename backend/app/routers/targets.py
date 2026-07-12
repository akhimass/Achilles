"""Target endpoints: ranked candidate targets with cited rationale."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("")
async def list_targets(
    strain_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """Ranked candidate targets for a strain, each with evidence + rationale.

    Phase 3 TODO: read targets ordered by rank_score; attach evidence edges; call
    ai/targets.narrate_target for the cited rationale.
    """
    _ = session, strain_id
    return {"targets": [], "todo": "Phase 3: target ranking + narration"}
