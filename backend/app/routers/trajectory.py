"""Trajectory endpoint: the retrieved counterfactual beat (never generated).

`GET /api/trajectory?strain_id=<id>&resisted=<DRUG>` returns what REAL evolved lineages
did after acquiring resistance to `<DRUG>` — retrieved and aggregated deterministically
by `ingestion/trajectories.py`, traced to specific real strains. The LLM (opt-in /
cached) only narrates the retrieved result; it never predicts or generates a trajectory.

On the public (PubMLST) path no resistance/sensitivity record exists, so the endpoint
honestly returns ``sufficient=false`` with a note — a gap is shown, never filled.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.domains import DEFAULT_ORGANISM
from app.ingestion.trajectories import LineageResSens, retrieve_trajectory

router = APIRouter(prefix="/api/trajectory", tags=["trajectory"])

_DEFAULT_ORGANISM = DEFAULT_ORGANISM

_STRAINS_SQL = """
    SELECT external_id, label,
           metadata->'resistance'  AS resistance,
           metadata->'sensitivity' AS sensitivity,
           metadata->'lineages'    AS lineages
    FROM strains
    WHERE organism = :organism AND metadata ? 'resistance'
"""


def _as_list(v) -> list[str]:
    """jsonb arrays may arrive as a Python list or a JSON string, depending on driver."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        import json

        try:
            parsed = json.loads(v)
            return [str(x) for x in parsed] if isinstance(parsed, list) else []
        except ValueError:
            return []
    return []


@router.get("")
async def trajectory(
    strain_id: str | None = None,
    resisted: str | None = None,
    organism: str = _DEFAULT_ORGANISM,
    narrate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Retrieve what real lineages did after a resistance event, then (opt-in) narrate."""
    event_strain: str | None = None
    resolved_org = organism

    if strain_id:
        srow = (
            await session.execute(
                text("SELECT external_id, organism, metadata->'resistance' AS resistance "
                     "FROM strains WHERE id = :id"),
                {"id": strain_id},
            )
        ).mappings().first()
        if srow is not None:
            event_strain = srow["external_id"]
            resolved_org = srow["organism"]
            if not resisted:
                # Default to the anchoring strain's own observed resistance (first drug).
                own = _as_list(srow["resistance"])
                resisted = own[0] if own else None

    if not resisted:
        # Nothing to retrieve against — honest empty result, not an error.
        from app.models.domain import TrajectoryEvidence

        return TrajectoryEvidence(
            organism=resolved_org, resisted="", event_strain=event_strain,
            sufficient=False,
            note="No resistance event specified (and the strain has no recorded resistance).",
            provenance={"method": "deterministic retrieval — no prediction"},
        ).model_dump()

    rows = (
        await session.execute(text(_STRAINS_SQL), {"organism": resolved_org})
    ).mappings().all()
    records = [
        LineageResSens(
            strain_id=r["external_id"],
            lineages=_as_list(r["lineages"]),
            resistance=_as_list(r["resistance"]),
            sensitivity=_as_list(r["sensitivity"]),
        )
        for r in rows
    ]

    evidence = retrieve_trajectory(
        records, resisted, organism=resolved_org, event_strain=event_strain
    )
    payload = evidence.model_dump()

    # Narration is optional enrichment of the RETRIEVED result; the data stands alone.
    narrative: dict | None = None
    source: str | None = None
    if evidence.sufficient:
        if narrate:
            narrative = await _narrate(evidence)
            source = "llm" if narrative else None
        else:
            from app.ai.narration_cache import trajectory_narrative

            narrative = trajectory_narrative(resolved_org, resisted)
            source = "cached" if narrative else None
    payload["narrative"] = narrative
    payload["narrative_source"] = source
    return payload


async def _narrate(evidence) -> dict | None:
    """Best-effort live narration; None if no key/network. Never raises, never predicts."""
    from app.ai.trajectory import narrate_trajectory

    try:
        result = await narrate_trajectory(evidence)
        if result and result.summary:
            return {"summary": result.summary, "citations": list(result.citations or []),
                    "source": "llm"}
    except Exception:
        return None
    return None
