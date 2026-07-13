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
from app.ingestion.domains import DEFAULT_ORGANISM
from app.ingestion.collateral import CollateralPair, propose_cycle
from app.treatment_shaping import shape_cycle

router = APIRouter(prefix="/api/treatment", tags=["treatment"])

_DEFAULT_ORGANISM = DEFAULT_ORGANISM

_CS_SQL = """
    SELECT organism, drug_a, drug_b, reciprocal, strength, n_lineages, metadata
    FROM collateral_sensitivity
    WHERE organism = :organism
    ORDER BY reciprocal DESC, n_lineages DESC NULLS LAST, drug_a, drug_b
"""


async def _anchor_for(
    session: AsyncSession, pairs: list[CollateralPair],
    strain_id: str | None, resisted: str | None,
) -> tuple[set[str] | None, dict | None]:
    """Resolve which reciprocal-graph drugs to anchor a cycle on.

    An explicit `resisted` drug wins; otherwise the selected strain's own recorded
    resistance profile is used. Matching is case-insensitive against the drugs actually
    present in the reciprocal-CS graph. Returns (start_drugs, anchor_block); a non-None
    anchor_block is always returned when a strain/resisted was supplied so the UI can be
    honest about whether personalization applied.
    """
    graph_drugs = {p.drug_a for p in pairs if p.reciprocal}
    canon = {d.lower(): d for d in graph_drugs}

    requested: list[str] = []
    strain_label: str | None = None
    if resisted:
        requested = [resisted]
    elif strain_id:
        srow = (
            await session.execute(
                text("SELECT external_id, label, metadata->'resistance' AS resistance "
                     "FROM strains WHERE id = :id"),
                {"id": strain_id},
            )
        ).mappings().first()
        if srow is not None:
            strain_label = srow["label"] or srow["external_id"]
            r = srow["resistance"]
            requested = list(r) if isinstance(r, list) else []

    if not requested:
        if strain_id or resisted:
            return None, {"anchored": False, "strain": strain_label,
                          "requested": [], "matched": [], "unmatched": [],
                          "reason": "No recorded resistance to anchor on — showing the general cycle."}
        return None, None

    matched = [canon[d.lower()] for d in requested if d.lower() in canon]
    unmatched = [d for d in requested if d.lower() not in canon]
    if not matched:
        return None, {"anchored": False, "strain": strain_label,
                      "requested": requested, "matched": [], "unmatched": unmatched,
                      "reason": "None of the strain's resistances are in the collateral-sensitivity "
                                "graph — showing the general cycle."}
    return set(matched), {"anchored": True, "strain": strain_label,
                          "requested": requested, "matched": matched, "unmatched": unmatched,
                          "reason": f"Cycle anchored to {matched[0]} (a drug this strain is resistant to)."}


@router.get("/cycle")
async def cycle(
    organism: str = _DEFAULT_ORGANISM,
    strain_id: str | None = None,
    resisted: str | None = None,
    narrate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Propose an antibiotic cycle for an organism, with cited (opt-in) narration.

    The cycle is computed from the reciprocal collateral-sensitivity graph; the LLM
    only narrates when `narrate=true`. When `strain_id` (or an explicit `resisted` drug)
    is given, the cycle is ANCHORED to a drug that strain is already resistant to.
    Degrades to an explicit empty state when no collateral data is seeded.
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

    starts, anchor = await _anchor_for(session, pairs, strain_id, resisted)
    proposed = propose_cycle(pairs, starts=starts) if starts else []
    if not proposed:
        # No anchored path (or no anchor requested) → the general longest cycle.
        proposed = propose_cycle(pairs)
        if anchor and anchor.get("anchored"):
            anchor["anchored"] = False
            anchor["reason"] = (f"{anchor['matched'][0]} is in the graph but starts no distinct "
                                "cycle — showing the general cycle.")

    narrative: dict | None = None
    narrative_source: str | None = None
    if proposed:
        if narrate:
            # Opt-in live override.
            narrative = await _narrate(organism, pairs, proposed)
            narrative_source = "llm" if narrative else None
        else:
            # Default: pre-reviewed committed narration (cached) when available.
            from app.ai.narration_cache import cycle_narrative

            narrative = cycle_narrative(organism)
            narrative_source = "cached" if narrative else None

    return shape_cycle(
        organism, proposed, pairs, narrative=narrative,
        narrative_source=narrative_source, anchor=anchor,
    )


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
