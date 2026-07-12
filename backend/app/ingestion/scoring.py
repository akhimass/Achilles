"""Deterministic candidate-target scoring — the Phase 3 heart.

A `rank_score` in [0, 1] is computed here in plain Python from two signals that are
already grounded upstream:

  1. Literature evidence support for the gene — how many evidence edges point at it,
     how confident they are, and (crucially) what fraction are *grounded* against a
     reference DB (CARD / UniProt). Provenance is the product; grounding is rewarded.
  2. Flipper strength — how strongly the gene reverses along the lineage (its
     `flipper_support`, produced by the deterministic flipper detector). A reversible
     gene is a better antibiotic-cycling / target candidate, so it lifts the score.

No LLM ever computes this number. `ai/targets.py` only narrates the result and must
not change it. Same input → same output; every transform here is unit-tested.

The knobs below are saturating constants, not global maxima, so `rank_score` is a
pure function of one gene's stats — no dependence on the rest of the batch. This
keeps the score stable as the corpus grows and makes it trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

# ─── Tunable, documented weights (all deterministic) ─────────────────────────

# Edge-count saturation: n/(n+K). K_EDGES=5 → 5 edges ≈ 0.5 volume, diminishing after.
K_EDGES = 5.0
# Flipper-support saturation: s/(s+K). K_FLIP=6 → support 6 ≈ 0.5, 9–10 ≈ 0.6–0.63.
K_FLIP = 6.0

# Within the evidence component, how much grounding vs. raw confidence matters.
W_GROUNDED = 0.6  # provenance-first: grounded fraction is weighted above bare conf
W_CONFIDENCE = 0.4
assert abs(W_GROUNDED + W_CONFIDENCE - 1.0) < 1e-9

# Top-level blend of the two signals into the final rank_score.
W_EVIDENCE = 0.7  # literature/grounding evidence dominates "is this a real target"
W_FLIPPER = 0.3  # reversibility adds AMR-cycling relevance
assert abs(W_EVIDENCE + W_FLIPPER - 1.0) < 1e-9


@dataclass(frozen=True)
class GeneEvidenceStats:
    """Per-gene inputs to scoring. All already computed deterministically upstream.

    `n_edges` / `mean_confidence` / `grounded_edges` summarize the gene's evidence
    edges; `flipper_support` is the lineage reversibility count from flipper detection
    (0 if the gene is not a flipper). This is a plain value object — no I/O.
    """

    gene_id: str
    locus_tag: str
    n_edges: int = 0
    mean_confidence: float = 0.0
    grounded_edges: int = 0
    flipper_support: int = 0

    @property
    def grounded_fraction(self) -> float:
        return (self.grounded_edges / self.n_edges) if self.n_edges else 0.0


@dataclass(frozen=True)
class TargetScore:
    """The scoring result, with its components exposed for transparent display.

    `rank_score` is the single 0–1 number persisted to `targets.rank_score`. The
    components are surfaced so the UI/rationale can show *why* deterministically,
    never asking the LLM to reconstruct the math.
    """

    gene_id: str
    locus_tag: str
    rank_score: float
    evidence_component: float
    flipper_component: float
    n_edges: int
    grounded_edges: int
    mean_confidence: float
    flipper_support: int


def _clamp01(x: float) -> float:
    if not isfinite(x):
        return 0.0
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _saturate(value: float, k: float) -> float:
    """Monotone saturating map [0, ∞) → [0, 1): value / (value + k)."""
    v = max(0.0, float(value))
    return v / (v + k) if (v + k) > 0 else 0.0


def evidence_component(stats: GeneEvidenceStats) -> float:
    """Volume × quality, where quality blends grounded fraction and mean confidence.

    Volume saturates with edge count so a single edge can't dominate; quality rewards
    grounded provenance above raw confidence. Zero edges → 0.0 (no literature support).
    """
    if stats.n_edges <= 0:
        return 0.0
    volume = _saturate(stats.n_edges, K_EDGES)
    quality = W_GROUNDED * _clamp01(stats.grounded_fraction) + W_CONFIDENCE * _clamp01(
        stats.mean_confidence
    )
    return _clamp01(volume * quality)


def flipper_component(stats: GeneEvidenceStats) -> float:
    """Saturating map of flipper support → [0, 1). Non-flippers (support 0) → 0.0."""
    return _clamp01(_saturate(stats.flipper_support, K_FLIP))


def rank_score(stats: GeneEvidenceStats) -> float:
    """Blend the evidence and flipper components into a single 0–1 rank score."""
    ev = evidence_component(stats)
    fl = flipper_component(stats)
    return _clamp01(W_EVIDENCE * ev + W_FLIPPER * fl)


def score_gene(stats: GeneEvidenceStats) -> TargetScore:
    """Full scoring result for one gene (rank_score plus its exposed components)."""
    ev = evidence_component(stats)
    fl = flipper_component(stats)
    score = _clamp01(W_EVIDENCE * ev + W_FLIPPER * fl)
    return TargetScore(
        gene_id=stats.gene_id,
        locus_tag=stats.locus_tag,
        rank_score=round(score, 4),
        evidence_component=round(ev, 4),
        flipper_component=round(fl, 4),
        n_edges=stats.n_edges,
        grounded_edges=stats.grounded_edges,
        mean_confidence=round(_clamp01(stats.mean_confidence), 4),
        flipper_support=stats.flipper_support,
    )


def rank_targets(stats: list[GeneEvidenceStats]) -> list[TargetScore]:
    """Score and rank a batch of genes, highest rank_score first.

    Deterministic tie-break: rank_score desc, then grounded edges desc, then edge
    count desc, then locus_tag asc — so the ordering never depends on input order.
    """
    scored = [score_gene(s) for s in stats]
    scored.sort(
        key=lambda t: (-t.rank_score, -t.grounded_edges, -t.n_edges, t.locus_tag)
    )
    return scored
