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


def _provenance(pair: CollateralPair | None) -> dict | None:
    """Citation view for a pair, when it comes from published literature."""
    if not pair:
        return None
    meta = pair.metadata or {}
    pmid = meta.get("pmid")
    if not pmid:
        return None
    return {
        "pmid": pmid,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "doi": meta.get("doi"),
        "source": meta.get("source") or "literature",
        "tier": meta.get("tier"),
    }


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
                "provenance": _provenance(pair),
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


def next_experiment(cycle: list[str], reciprocal: list[CollateralPair]) -> dict | None:
    """The single highest-leverage wet-lab test implied by the cycle — deterministic,
    grounded in lineage support. Turns the hypothesis into one concrete next step.
    `reciprocal` must be pre-sorted by descending support (as shape_cycle does)."""
    if not cycle or not reciprocal:
        return None
    p = reciprocal[0]
    prov = _provenance(p)
    n = p.n_lineages or 0
    if prov and not p.n_lineages:
        # Literature-reported reciprocal CS — cite it rather than invent a lineage count.
        detail = (
            f"Challenge {p.drug_a}-resistant isolates with {p.drug_b}: this reciprocal "
            f"re-sensitization is reported in B. multivorans (PMID {prov['pmid']}). "
            f"Confirming it in your isolates anchors the {p.drug_a} ⇄ {p.drug_b} cycle above."
        )
    else:
        lin = f"{n} evolved lineage{'' if n == 1 else 's'}"
        detail = (
            f"Challenge {p.drug_a}-resistant isolates with {p.drug_b}: {lin} in this cohort "
            f"show that reversal. If it holds in vitro, the {p.drug_a} ⇄ {p.drug_b} pair "
            "anchors the cycle above."
        )
    return {
        "drug_a": p.drug_a,
        "drug_b": p.drug_b,
        "n_lineages": n,
        "provenance": prov,
        "headline": f"Test {p.drug_a} → {p.drug_b} re-sensitization",
        "detail": detail,
    }


def shape_cycle(
    organism: str,
    cycle: list[str],
    pairs: list[CollateralPair],
    narrative: dict | None = None,
    narrative_source: str | None = None,
    anchor: dict | None = None,
) -> dict:
    """Assemble the /api/treatment/cycle payload. Pure; never alters the cycle.

    `narrative` is an optional LLM narration block; `narrative_source` labels it
    (`"cached"` for pre-reviewed committed narration, `"llm"` for a live call) so the
    UI can be honest about what produced it. The deterministic `summary` is always
    present regardless, and the cycle itself is never touched by narration.
    """
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
            "source": narrative_source,
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
                "provenance": _provenance(p),
            }
            for p in reciprocal
        ],
        "anchor": anchor,
        "narrative": narr_block,
        "narrative_source": narrative_source if narr_block else None,
        "next_experiment": next_experiment(cycle, reciprocal),
        "is_hypothesis": True,
        "caveats": caveats,
        "counts": {
            "pairs": len(pairs),
            "reciprocal": len(reciprocal),
            "cited": sum(1 for p in reciprocal if _provenance(p)),
            "cycle_length": len(cycle),
        },
    }
