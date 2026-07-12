"""Lineage helpers: assemble the parent map the flipper detector needs, reconstruct
a lineage from MLST genotypes, and annotate variants against reference genes.

Kept separate from flippers.py so annotation and lineage reconstruction can grow
without touching the detection algorithm. Everything here is deterministic and
network-free (no LLM, no I/O).
"""

from __future__ import annotations

from typing import Hashable
from uuid import UUID

from app.models.domain import Strain, Variant

# MLST loci in canonical order (mirror of parsers.MLST_LOCI; kept local so the
# ingestion layer has no cross-module coupling for a 7-item constant).
MLST_LOCI: tuple[str, ...] = ("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB")


def parent_map(strains: list[Strain]) -> dict[UUID, UUID | None]:
    """Build {strain_id: parent_id} for build_lineage_paths()."""
    return {s.id: s.parent_id for s in strains if s.id is not None}


def allelic_distance(a: dict[str, int], b: dict[str, int]) -> int:
    """Number of MLST loci at which two profiles differ (0..7). Hamming over loci."""
    return sum(1 for locus in MLST_LOCI if a.get(locus) != b.get(locus))


def build_mst_lineage(records: list[dict]) -> dict[Hashable, Hashable | None]:
    """Reconstruct a lineage as a minimum spanning tree over MLST allelic distance.

    An MST over allelic distance is the standard way MLST relationships are drawn
    (goeBURST / PHYLOViZ): each isolate attaches to its nearest already-placed
    relative, so edges are real genotype similarities rather than an invented order.
    It is a reconstruction, not a dated phylogeny — but it is deterministic and data
    driven, which is what Phase 1 needs to give the flipper detector real paths.

    Input: records with keys `id` (hashable), `profile` (locus->allele), and `year`.
    Output: {id: parent_id}, with a single root mapped to None. Root = earliest year
    then smallest id; ties throughout break on (distance, year, id, parent-id) so the
    tree is identical on every run.
    """
    if not records:
        return {}

    by_id = {r["id"]: r for r in records}

    def year_of(r: dict) -> int:
        try:
            return int(r["year"])
        except (TypeError, ValueError, KeyError):
            return 1 << 30  # undated sorts last

    order = sorted(records, key=lambda r: (year_of(r), r["id"]))
    root = order[0]["id"]
    parent: dict[Hashable, Hashable | None] = {root: None}
    inside = {root}
    remaining = {r["id"] for r in records if r["id"] != root}

    while remaining:
        best_key = None
        best_child = best_parent = None
        for child in remaining:
            cr = by_id[child]
            for anchor in inside:
                d = allelic_distance(cr["profile"], by_id[anchor]["profile"])
                key = (d, year_of(cr), child, anchor)
                if best_key is None or key < best_key:
                    best_key, best_child, best_parent = key, child, anchor
        parent[best_child] = best_parent
        inside.add(best_child)
        remaining.discard(best_child)

    return parent


def annotate_effects(
    variants: list[Variant], gene_by_locus: dict[str, UUID] | None = None
) -> list[Variant]:
    """Assign gene_id / effect to variants from reference annotation.

    When `gene_by_locus` is supplied (locus symbol -> gene UUID), each variant's
    `gene_id` is set from its `metadata['locus']`. `effect` is left None: an MLST
    allele change is a housekeeping-locus substitution whose codon-level effect is
    not resolved at this stage (nullable by contract). Without a lookup this is a
    no-op, preserving the original contract: same list back, fields filled where
    annotation is available.
    """
    if not gene_by_locus:
        return variants
    for v in variants:
        locus = v.metadata.get("locus")
        if locus in gene_by_locus:
            v.gene_id = gene_by_locus[locus]
    return variants
