"""Collateral-sensitivity structure and antibiotic-cycle proposal.

All deterministic. Given per-lineage resistance/sensitivity transitions, compute
which drug pairs show collateral sensitivity (resistance to A -> sensitivity to B),
mark reciprocal pairs (RCS), and propose a cycle from the RCS graph.

The LLM (ai/treatment.py) only narrates the output of this module. It never runs
any of this logic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.models.domain import CollateralPair


@dataclass
class SensitivityObservation:
    """One observed transition in one lineage: acquiring resistance to `resisted`
    coincided with increased sensitivity to `sensitized`."""

    lineage_id: str
    resisted: str
    sensitized: str


def compute_collateral_pairs(
    observations: list[SensitivityObservation], organism: str, *, min_lineages: int = 1
) -> list[CollateralPair]:
    """Aggregate observations into CS pairs and flag reciprocal (RCS) ones."""
    support: dict[tuple[str, str], set[str]] = defaultdict(set)
    for o in observations:
        support[(o.resisted, o.sensitized)].add(o.lineage_id)

    directed = {pair: lineages for pair, lineages in support.items() if len(lineages) >= min_lineages}

    pairs: list[CollateralPair] = []
    for (a, b), lineages in directed.items():
        reciprocal = (b, a) in directed
        pairs.append(
            CollateralPair(
                organism=organism,
                drug_a=a,
                drug_b=b,
                reciprocal=reciprocal,
                strength=round(len(lineages) / max(len(observations), 1), 4),
                n_lineages=len(lineages),
            )
        )
    return sorted(pairs, key=lambda p: (not p.reciprocal, -(p.n_lineages or 0)))


def propose_cycle(
    pairs: list[CollateralPair], *, max_len: int = 4, starts: set[str] | None = None
) -> list[str]:
    """Propose an antibiotic cycle by walking the reciprocal-CS graph.

    Greedy longest-simple-path over RCS edges: each hop goes to a drug the current
    one sensitizes toward (and back), which is exactly the property that lets an
    alternating regimen keep resistance from fixing. Returns an ordered drug list.
    This is a hypothesis generator, not a treatment plan.

    When `starts` is given, only paths beginning at one of those drugs are considered —
    this is how a cycle is *anchored* to a specific strain's current resistance (start
    from a drug it is already resistant to, then alternate). Drugs in `starts` that
    aren't in the reciprocal graph are ignored; if none remain, returns [].
    """
    adj: dict[str, list[str]] = defaultdict(list)
    for p in pairs:
        if p.reciprocal:
            adj[p.drug_a].append(p.drug_b)

    start_nodes = list(adj) if starts is None else [s for s in adj if s in starts]

    best: list[str] = []

    def walk(node: str, visited: list[str]) -> None:
        nonlocal best
        if len(visited) > len(best):
            best = list(visited)
        if len(visited) >= max_len:
            return
        for nxt in adj[node]:
            if nxt not in visited:
                walk(nxt, [*visited, nxt])

    for start in start_nodes:
        walk(start, [start])
    return best
