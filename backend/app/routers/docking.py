"""Docking / druggability endpoint — the tractability→structure→inhibitor tie.

`GET /api/docking` returns, for each target with a cited known inhibitor, the ligand
(with its grounding), plus any Tamarind results computed so far: ADMET drug properties
and a docking pose/score into the AlphaFold structure. Deterministic read of the
committed cache; the live Tamarind runs happen via `python -m app.sources.dock`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.ai.docking_cache import load_ligands, load_result, shape_all, shape_docking

router = APIRouter(prefix="/api/docking", tags=["docking"])


@router.get("")
async def docking(locus: str | None = None) -> dict:
    """All ligand-bearing targets (or one), with cited ligands + any Tamarind results."""
    if locus:
        ligs = load_ligands().get(locus, [])
        return shape_docking(locus, ligs, load_result(locus))
    return shape_all()
