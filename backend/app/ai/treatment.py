"""Treatment narration: explain a deterministically-computed antibiotic cycle.

The cycle and the reciprocal-CS pairs come from ingestion/collateral.py. Claude
explains and caveats — it never designs the cycle. This separation is the point:
the clinical-facing logic is auditable Python; the LLM is the narration layer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import structured
from app.config import settings
from app.models.domain import CollateralPair


class TreatmentNarrative(BaseModel):
    summary: str
    caveats: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


async def narrate_cycle(
    *, organism: str, rcs_pairs: list[CollateralPair], cycle: list[str], evidence: str
) -> TreatmentNarrative:
    """Explain a proposed cycling schedule with citations and caveats."""
    pairs_txt = "\n".join(
        f"- {p.drug_a} <-> {p.drug_b} (strength {p.strength}, n={p.n_lineages})"
        for p in rcs_pairs
    )
    return await structured(
        schema=TreatmentNarrative,
        system=prompts.TREATMENT_SYSTEM,
        user=prompts.TREATMENT_USER.format(
            organism=organism,
            rcs_pairs=pairs_txt or "(none)",
            cycle=" -> ".join(cycle),
            evidence=evidence,
        ),
        model=settings.model_reason,
    )
