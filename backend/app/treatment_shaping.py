"""Pure view-model transforms for the treatment (cycling) endpoint (Phase 4).

The cycle and the reciprocal-CS pairs are computed deterministically upstream
(ingestion/collateral.py). This module only arranges them for the UI and attaches the
mandatory research-hypothesis framing. It never designs or reorders the cycle, and it
imports no DB / LLM / driver code so it stays unit-testable.
"""

from __future__ import annotations

from app.models.domain import CollateralPair

# Always shown, regardless of any LLM narration. Cycling is a hypothesis, never advice.
_DEFAULT_CAVEATS = [
    "This is a research hypothesis from in-vitro collateral-sensitivity structure — "
    "not a treatment recommendation.",
    "Collateral sensitivity is frequently non-reciprocal and can be strain- and "
    "lineage-specific; the strengths here are lineage-support counts, not clinical efficacy.",
    "No pharmacokinetics, dosing, toxicity, or in-vivo validation is modeled.",
]


def _pair_index(pairs: list[CollateralPair]) -> dict[tuple[str, str], CollateralPair]:
    return {(p.drug_a, p.drug_b): p for p in pairs}


def _steps(cycle: list[str], idx: dict[tuple[str, str], CollateralPair]) -> list[dict]:
    """Consecutive hops of the cycle (wrapping back to the start), annotated from the
    computed pairs. `reciprocal`/support come straight from the deterministic pairs."""
    steps: list[dict] = []
    n = len(cycle)
    if n < 2:
        return steps
    for i in range(n):
        a = cycle[i]
        b = cycle[(i + 1) % n]
        if i == n - 1 and n == 2:
            break  # a 2-cycle wrapping would duplicate the single edge
        pair = idx.get((a, b))
        steps.append(
            {
                "from": a,
                "to": b,
                "reciprocal": bool(pair.reciprocal) if pair else False,
                "n_lineages": (pair.n_lineages if pair else None),
                "strength": (pair.strength if pair else None),
                "closes_loop": i == n - 1,
            }
        )
    return steps


def deterministic_summary(cycle: list[str], reciprocal: list[CollateralPair]) -> str:
    """A factual one-liner describing the computed cycle (no LLM, no invention)."""
    if not cycle:
        return (
            "No reciprocal collateral-sensitivity loop was found in the current data, "
            "so no cycle is proposed."
        )
    n_lin = sorted({l for p in reciprocal for l in [p.n_lineages or 0]}, reverse=True)
    max_lin = n_lin[0] if n_lin else 0
    arrow = " → ".join(cycle)
    return (
        f"Proposed {len(cycle)}-drug alternating cycle {arrow}, walked over "
        f"{len(reciprocal)} reciprocal collateral-sensitivity pairs (up to {max_lin} "
        "lineages of support). Alternating between reciprocally sensitizing drugs is "
        "hypothesized to keep resistance from fixing."
    )


def shape_cycle(
    organism: str,
    cycle: list[str],
    pairs: list[CollateralPair],
    narrative: dict | None = None,
) -> dict:
    """Assemble the /api/treatment/cycle payload. Pure; never alters the cycle."""
    idx = _pair_index(pairs)
    reciprocal = [p for p in pairs if p.reciprocal]
    reciprocal.sort(key=lambda p: (-(p.n_lineages or 0), p.drug_a, p.drug_b))

    caveats = list(_DEFAULT_CAVEATS)
    narr_block: dict | None = None
    if narrative:
        narr_block = {
            "summary": narrative.get("summary"),
            "caveats": narrative.get("caveats") or [],
            "citations": narrative.get("citations") or [],
        }
        for c in narr_block["caveats"]:
            if c and c not in caveats:
                caveats.append(c)

    return {
        "organism": organism,
        "cycle": cycle,
        "summary": deterministic_summary(cycle, reciprocal),
        "steps": _steps(cycle, idx),
        "rcs_pairs": [
            {
                "drug_a": p.drug_a,
                "drug_b": p.drug_b,
                "reciprocal": p.reciprocal,
                "n_lineages": p.n_lineages,
                "strength": p.strength,
            }
            for p in reciprocal
        ],
        "narrative": narr_block,
        "is_hypothesis": True,
        "caveats": caveats,
        "counts": {
            "pairs": len(pairs),
            "reciprocal": len(reciprocal),
            "cycle_length": len(cycle),
        },
    }
