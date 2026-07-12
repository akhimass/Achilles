"""Deterministic trajectory retrieval — the counterfactual beat's real engine.

Given a resistance event (a strain acquired resistance to drug A), this RETRIEVES from
the real lineage record what those lineages actually did next: which drugs became
sensitive again ("viable"), across how many distinct lineages, and backed by exactly
which real strains. It aggregates observed transitions that are already in the data.

The non-negotiable line: this NEVER predicts, simulates, or generates a trajectory,
mutation, or outcome. It only reports observed reality with its provenance. If the data
supports no answer, it returns ``sufficient=False`` with an honest note — a gap is shown,
never filled. No LLM, no network here; the LLM (ai/trajectory.py) only narrates output.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.domain import ObservedNext, TrajectoryEvidence

_PROVENANCE = {
    "source": "experimental-evolution lineages (observed resistance/sensitivity transitions)",
    "method": (
        "deterministic retrieval + aggregation over real observed transitions — "
        "no prediction, simulation, or generation"
    ),
}


@dataclass
class LineageResSens:
    """One real strain's observed resistance/sensitivity profile and lineage membership.

    Plain value object so tests build synthetic fixtures without any private data.
    """

    strain_id: str
    lineages: list[str] = field(default_factory=list)
    resistance: list[str] = field(default_factory=list)
    sensitivity: list[str] = field(default_factory=list)


def _natural(strain_id: str) -> tuple[int, str]:
    """Sort key: numeric strain ids (e.g. '167') sort numerically, others lexically."""
    return (int(strain_id), "") if strain_id.isdigit() else (1 << 62, strain_id)


def retrieve_trajectory(
    records: list[LineageResSens],
    resisted: str,
    *,
    organism: str,
    event_strain: str | None = None,
) -> TrajectoryEvidence:
    """Retrieve what real lineages did after acquiring resistance to `resisted`.

    Aggregates the drugs that became sensitive again across the real strains resistant
    to `resisted`, with distinct-lineage support and the exact backing strain ids.
    Pure and deterministic: same input → same output; ordering never depends on input
    order. Nothing is inferred beyond what the records directly state.
    """
    backing = [r for r in records if resisted in (r.resistance or [])]

    # All observed directed (resisted → sensitized) transitions, to flag reciprocity.
    directed: set[tuple[str, str]] = set()
    for r in records:
        for a in r.resistance or []:
            for b in r.sensitivity or []:
                if a != b:
                    directed.add((a, b))

    by_drug: dict[str, dict[str, set]] = {}
    for r in backing:
        for b in r.sensitivity or []:
            if b == resisted:
                continue  # a drug can't be its own collateral outcome
            slot = by_drug.setdefault(b, {"strains": set(), "lineages": set()})
            slot["strains"].add(r.strain_id)
            slot["lineages"].update(r.lineages or [])

    observed = [
        ObservedNext(
            sensitized_to=drug,
            n_lineages=len(v["lineages"]),
            n_strains=len(v["strains"]),
            backing_strains=sorted(v["strains"], key=_natural),
            lineages=sorted(v["lineages"]),
            # Reciprocal iff the reverse (drug resisted → resisted-drug sensitive) is
            # ALSO observed in real data — the property a cycle exploits.
            reciprocal=(drug, resisted) in directed,
        )
        for drug, v in by_drug.items()
    ]
    observed.sort(key=lambda o: (-o.n_lineages, -o.n_strains, o.sensitized_to))

    support_lineages = len({l for r in backing for l in (r.lineages or [])})
    all_backing = sorted({r.strain_id for r in backing}, key=_natural)
    sufficient = bool(backing) and bool(observed)

    note: str | None = None
    if not backing:
        note = (
            f"No lineage in the dataset acquired resistance to {resisted}, so there is "
            "no real trajectory to show."
        )
    elif not observed:
        note = (
            f"Resistance to {resisted} was observed, but no collateral sensitivity "
            "co-occurred in the record."
        )

    return TrajectoryEvidence(
        organism=organism,
        resisted=resisted,
        event_strain=event_strain,
        observed_next=observed,
        support_lineages=support_lineages,
        backing_strains=all_backing,
        reciprocal_count=sum(1 for o in observed if o.reciprocal),
        sufficient=sufficient,
        kind="retrieved",
        note=note,
        provenance=dict(_PROVENANCE),
    )
