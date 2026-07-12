"""NCBI Pathogen Detection adapter — AMR genotypes and isolates (public)."""

from __future__ import annotations

from app.config import settings
from app.models.domain import Strain


async def fetch_isolates(organism: str, *, limit: int = 500) -> list[Strain]:
    """Fetch isolates + AMR genotype calls for an organism.

    Phase 1 TODO: pull from the Pathogen Detection Isolates Browser / AMRFinderPlus
    outputs; map to Strain rows. Alternative supplier to BV-BRC.
    """
    _ = settings, organism, limit
    raise NotImplementedError("Phase 1: implement NCBI Pathogen Detection fetch")
