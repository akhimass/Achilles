"""Trajectory narration: explain a RETRIEVED counterfactual in plain language.

The trajectory — what real lineages did after a resistance event — is retrieved and
aggregated deterministically by ``ingestion/trajectories.py``. Claude only narrates the
retrieved reality and cites the backing strains. It must never predict, simulate, or
generate a trajectory; the prompt forbids forecast language. This is the whole point:
the counterfactual is observed, not invented.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import structured
from app.config import settings
from app.models.domain import TrajectoryEvidence


class TrajectoryNarrative(BaseModel):
    summary: str
    citations: list[str] = Field(default_factory=list)


async def narrate_trajectory(evidence: TrajectoryEvidence) -> TrajectoryNarrative:
    """Narrate a retrieved trajectory with citations to its backing strains."""
    observed = "\n".join(
        f"- {o.sensitized_to} became viable in {o.n_lineages} lineage(s), "
        f"{o.n_strains} strain(s): {', '.join(o.backing_strains[:8])}"
        for o in evidence.observed_next
    ) or "(insufficient real evidence — no observed collateral outcome)"
    event = f", anchored on strain {evidence.event_strain}" if evidence.event_strain else ""
    backing = ", ".join(evidence.backing_strains[:12]) or "(none)"
    return await structured(
        schema=TrajectoryNarrative,
        system=prompts.TRAJECTORY_SYSTEM,
        user=prompts.TRAJECTORY_USER.format(
            organism=evidence.organism,
            resisted=evidence.resisted,
            event=event,
            observed=observed,
            backing=backing,
        ),
        model=settings.model_reason,
    )
