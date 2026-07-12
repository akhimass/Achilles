"""Flipper detection — the deterministic heart of the domain.

A "flipper" is a genomic site whose allele state reverses (reference <-> alternate)
across sequential steps of an evolutionary lineage. These reversible sites are the
genomic correlate of collateral sensitivity, so detecting them cleanly is the whole
point of the upstream pipeline.

This is a fresh, generic implementation over the typed `Variant`/lineage contract —
not a port of any prior codebase. It's deterministic: same input, same output.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from app.models.domain import Variant, VariantKind

# Canonical MLST loci order (mirror of parsers/lineage) for the allele expansion.
_MLST_LOCI: tuple[str, ...] = ("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB")


@dataclass
class LineagePath:
    """An ordered root->leaf path of strain ids through the lineage tree."""

    strain_ids: list[UUID]


@dataclass
class FlipperSite:
    """A genomic position that flips allele state along at least one lineage path."""

    ref_position: int
    kind: str
    transitions: int = 0  # number of state changes observed along paths
    max_allele_freq: float = 0.0
    supporting_paths: int = 0
    strain_ids: list[UUID] = field(default_factory=list)


def build_lineage_paths(parent_of: dict[UUID, UUID | None]) -> list[LineagePath]:
    """Turn a parent map into root->leaf paths.

    `parent_of[strain] == None` marks a root. Every leaf yields one path.
    """
    children: dict[UUID | None, list[UUID]] = defaultdict(list)
    for node, parent in parent_of.items():
        children[parent].append(node)
    leaves = [n for n in parent_of if not children.get(n)]

    def path_to_root(node: UUID) -> list[UUID]:
        seq = [node]
        while (p := parent_of.get(seq[-1])) is not None:
            seq.append(p)
        return list(reversed(seq))

    return [LineagePath(path_to_root(leaf)) for leaf in leaves]


def detect_flippers(
    variants_by_strain: dict[UUID, list[Variant]],
    paths: list[LineagePath],
    *,
    min_allele_freq: float = 0.05,
) -> list[FlipperSite]:
    """Find sites whose allele state reverses along lineage paths.

    Algorithm (deterministic):
      For each position, walk each lineage path in order and record whether the
      alt allele is present (freq >= threshold) at each strain. A "transition" is
      any step where presence changes. A site with >=2 transitions along a path has
      reverted at least once (present -> absent -> present or the reverse) and is a
      flipper. We aggregate transitions and support across all paths.
    """
    # position -> strain -> present(bool)
    present: dict[tuple[int, str], dict[UUID, bool]] = defaultdict(dict)
    max_af: dict[tuple[int, str], float] = defaultdict(float)
    for strain_id, variants in variants_by_strain.items():
        for v in variants:
            key = (v.ref_position, v.kind.value)
            is_present = (v.allele_freq or 0.0) >= min_allele_freq
            present[key][strain_id] = is_present
            max_af[key] = max(max_af[key], v.allele_freq or 0.0)

    sites: dict[tuple[int, str], FlipperSite] = {}
    for key, strain_present in present.items():
        pos, kind = key
        total_transitions = 0
        supporting = 0
        involved: set[UUID] = set()
        for path in paths:
            states = [strain_present.get(sid) for sid in path.strain_ids]
            seq = [s for s in states if s is not None]
            if len(seq) < 3:
                continue
            transitions = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
            if transitions >= 2:  # reversal happened at least once
                total_transitions += transitions
                supporting += 1
                involved.update(sid for sid in path.strain_ids if sid in strain_present)
        if supporting:
            sites[key] = FlipperSite(
                ref_position=pos,
                kind=kind,
                transitions=total_transitions,
                max_allele_freq=max_af[key],
                supporting_paths=supporting,
                strain_ids=sorted(involved, key=str),
            )

    # Deterministic order: most-supported, then most transitions, then position.
    return sorted(
        sites.values(),
        key=lambda s: (-s.supporting_paths, -s.transitions, s.ref_position),
    )


def detect_mlst_flippers(
    profiles_by_strain: dict[UUID, dict[str, int]],
    paths: list[LineagePath],
    loci: tuple[str, ...] | list[str] = _MLST_LOCI,
) -> dict[UUID, set[tuple[str, int]]]:
    """Find MLST (locus, allele) states that reverse across the lineage, per strain.

    An MLST allele change is an identity switch (allele A -> B -> A), not a
    presence/absence event, so we reduce it to the presence model `detect_flippers`
    already implements: for every (locus, allele) seen in the dataset, each strain
    is `present` (freq 1.0) if it carries that allele at that locus and `absent`
    (freq 0.0) otherwise. A (locus, allele) that goes present -> absent -> present
    along a path is a reversal. This reuses the tested detector verbatim rather than
    forking the reversal logic.

    Attribution is per strain: a strain maps to the reverting (locus, allele) sites
    whose supporting (reverting) paths pass through it, so flipper density reflects
    each strain's own lineage — not the whole tree. Returns {strain_id: {(locus,
    allele), ...}}.
    """
    # allele universe per locus
    universe: dict[str, set[int]] = {locus: set() for locus in loci}
    for prof in profiles_by_strain.values():
        for locus, allele in prof.items():
            if locus in universe:
                universe[locus].add(allele)

    # encode each (locus, allele) as a distinct synthetic position
    def encode(locus_idx: int, allele: int) -> int:
        return locus_idx * 1_000_000 + allele

    decode: dict[int, tuple[str, int]] = {}
    synthetic: dict[UUID, list[Variant]] = {sid: [] for sid in profiles_by_strain}
    for locus_idx, locus in enumerate(loci):
        for allele in universe[locus]:
            pos = encode(locus_idx, allele)
            decode[pos] = (locus, allele)
            for sid, prof in profiles_by_strain.items():
                present = prof.get(locus) == allele
                synthetic[sid].append(
                    Variant(
                        strain_id=sid,
                        kind=VariantKind.snp,
                        ref_position=pos,
                        allele_freq=1.0 if present else 0.0,
                    )
                )

    sites = detect_flippers(synthetic, paths, min_allele_freq=0.5)
    per_strain: dict[UUID, set[tuple[str, int]]] = {sid: set() for sid in profiles_by_strain}
    for site in sites:
        pair = decode.get(site.ref_position)
        if pair is None:
            continue
        for sid in site.strain_ids:
            per_strain[sid].add(pair)
    return per_strain
