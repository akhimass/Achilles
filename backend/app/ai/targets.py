"""Target reasoning: rank candidate targets and write a cited rationale.

The rank_score is computed deterministically (see ingestion/scoring in Phase 3) and
passed in. Claude only narrates why, citing the evidence edges. It must not change
the score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import structured
from app.config import settings


class TargetRationale(BaseModel):
    narrative: str
    citations: list[str] = Field(default_factory=list)


async def narrate_target(
    *, gene: str, product: str, rank_score: float, edges: str, tractability: str
) -> TargetRationale:
    """Produce a cited, plain-language rationale for a candidate target."""
    return await structured(
        schema=TargetRationale,
        system=prompts.TARGET_SYSTEM,
        user=prompts.TARGET_USER.format(
            gene=gene,
            product=product,
            rank_score=rank_score,
            edges=edges,
            tractability=tractability,
        ),
        model=settings.model_reason,
    )
