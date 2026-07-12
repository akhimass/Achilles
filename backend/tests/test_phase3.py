"""Phase 3 tests: deterministic target scoring. No DB, no network, no LLM.

These lock the rank_score invariants: it stays in [0, 1], grounding and flipper
strength move it in the expected direction, and the batch ranking is a pure function
of the inputs (independent of their order).
"""

from __future__ import annotations

from app.ingestion.scoring import (
    GeneEvidenceStats,
    evidence_component,
    flipper_component,
    rank_score,
    rank_targets,
    score_gene,
)


def _stats(**kw) -> GeneEvidenceStats:
    base = dict(gene_id="g", locus_tag="LOCUS", n_edges=0, mean_confidence=0.0,
                grounded_edges=0, flipper_support=0)
    base.update(kw)
    return GeneEvidenceStats(**base)


# ─── Bounds ──────────────────────────────────────────────────────────────────


def test_rank_score_bounded_0_1_across_extremes():
    extremes = [
        _stats(),
        _stats(n_edges=1000, mean_confidence=1.0, grounded_edges=1000, flipper_support=10_000),
        _stats(n_edges=1, mean_confidence=1.0, grounded_edges=1, flipper_support=1),
        _stats(mean_confidence=5.0, grounded_edges=3, n_edges=1),  # out-of-range conf clamps
    ]
    for s in extremes:
        assert 0.0 <= rank_score(s) <= 1.0


def test_empty_gene_scores_zero():
    s = _stats()
    assert rank_score(s) == 0.0
    assert evidence_component(s) == 0.0
    assert flipper_component(s) == 0.0


def test_zero_edges_uses_flipper_only():
    # A flipper gene with no literature edges still gets a (small) score from reversal.
    s = _stats(n_edges=0, flipper_support=10)
    assert evidence_component(s) == 0.0
    assert rank_score(s) > 0.0
    assert flipper_component(s) > 0.0


# ─── Monotonicity: grounding, confidence, volume, flipper all lift the score ──


def test_grounding_raises_score():
    ungrounded = _stats(n_edges=8, mean_confidence=0.8, grounded_edges=0, flipper_support=5)
    grounded = _stats(n_edges=8, mean_confidence=0.8, grounded_edges=8, flipper_support=5)
    assert rank_score(grounded) > rank_score(ungrounded)


def test_more_confident_edges_raise_score():
    lo = _stats(n_edges=6, mean_confidence=0.4, grounded_edges=3)
    hi = _stats(n_edges=6, mean_confidence=0.9, grounded_edges=3)
    assert rank_score(hi) > rank_score(lo)


def test_more_edges_raise_evidence_component():
    few = _stats(n_edges=2, mean_confidence=0.8, grounded_edges=2)
    many = _stats(n_edges=20, mean_confidence=0.8, grounded_edges=20)
    assert evidence_component(many) > evidence_component(few)


def test_flipper_component_saturates_and_is_monotone():
    a = flipper_component(_stats(flipper_support=3))
    b = flipper_component(_stats(flipper_support=9))
    c = flipper_component(_stats(flipper_support=100))
    assert a < b < c < 1.0  # monotone increasing, never reaches 1


# ─── The demo anchor: MarR is a strong target; a thin gene is not ────────────


def test_marr_like_gene_outranks_thin_gene():
    marr = _stats(gene_id="marr", locus_tag="A8H40_RS07590", n_edges=11,
                  mean_confidence=0.86, grounded_edges=7, flipper_support=10)
    thin = _stats(gene_id="thin", locus_tag="A8H40_RS00780", n_edges=1,
                  mean_confidence=0.5, grounded_edges=0, flipper_support=9)
    assert rank_score(marr) > rank_score(thin)
    assert rank_score(marr) >= 0.4  # a genuinely strong, grounded candidate


def test_rank_targets_orders_and_is_input_order_independent():
    a = _stats(gene_id="a", locus_tag="AAA", n_edges=11, mean_confidence=0.86,
               grounded_edges=7, flipper_support=10)
    b = _stats(gene_id="b", locus_tag="BBB", n_edges=24, mean_confidence=0.9,
               grounded_edges=24, flipper_support=9)
    c = _stats(gene_id="c", locus_tag="CCC", n_edges=1, mean_confidence=0.4,
               grounded_edges=0, flipper_support=9)
    order1 = [t.locus_tag for t in rank_targets([a, b, c])]
    order2 = [t.locus_tag for t in rank_targets([c, b, a])]
    assert order1 == order2  # deterministic, order-independent
    assert order1[0] == "BBB"  # fully-grounded, high-volume gene ranks first
    assert order1[-1] == "CCC"  # thin single-edge gene ranks last


def test_score_gene_exposes_rounded_components():
    t = score_gene(_stats(n_edges=11, mean_confidence=0.86, grounded_edges=7, flipper_support=10))
    # Components are exposed and consistent with the blended score (0.7/0.3).
    assert 0.0 <= t.evidence_component <= 1.0
    assert 0.0 <= t.flipper_component <= 1.0
    blended = round(0.7 * t.evidence_component + 0.3 * t.flipper_component, 4)
    assert abs(t.rank_score - blended) <= 0.0002
