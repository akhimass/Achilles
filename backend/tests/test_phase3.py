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
from app.ingestion.seed_targets import _target_id, build_target, build_targets
from app.sources import chembl
from app.targets_shaping import deterministic_rationale, shape_target, shape_targets


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


# ─── Target model construction (seed_targets, pure) ──────────────────────────


def _row(**kw) -> dict:
    base = dict(gene_id="00000000-0000-0000-0000-000000000001", locus_tag="A8H40_RS07590",
                name="MarR", product="MarR family regulator", wp="WP_006410546.1",
                flipper_support=10, n_edges=11, mean_confidence=0.86, grounded_edges=7)
    base.update(kw)
    return base


def test_build_target_carries_score_mechanism_and_tractability():
    t = build_target(_row())
    # rank_score matches the deterministic scorer exactly (LLM never touches it).
    expected = score_gene(GeneEvidenceStats(
        gene_id="x", locus_tag="A8H40_RS07590", n_edges=11, mean_confidence=0.86,
        grounded_edges=7, flipper_support=10)).rank_score
    assert t.rank_score == expected
    assert 0.0 <= t.rank_score <= 1.0
    assert "MarR" in (t.mechanism or "")  # mapped mechanism, not raw product
    assert t.tractability.get("source") == "ChEMBL"  # tractability block always attached
    assert t.metadata["locus_tag"] == "A8H40_RS07590"
    assert t.metadata["uniprot_acc"] == "A0A0H3KEU2"
    assert "score_components" in t.metadata
    assert t.pdb_ids == []  # AlphaFold structures reached via /api/structure by locus


def test_build_target_id_is_stable_uuid5():
    a = build_target(_row())
    b = build_target(_row())
    assert a.id == b.id == _target_id(_row()["gene_id"])  # idempotent id


def test_build_targets_ranks_marr_first():
    rows = [
        _row(gene_id="00000000-0000-0000-0000-000000000002", locus_tag="A8H40_RS00780",
             name="response regulator", product="response regulator", n_edges=1,
             mean_confidence=0.5, grounded_edges=0, flipper_support=9),
        _row(),  # MarR: many grounded edges + strong flipper
    ]
    ranked = build_targets(rows)
    assert ranked[0].metadata["locus_tag"] == "A8H40_RS07590"
    assert ranked[0].rank_score >= ranked[-1].rank_score


# ─── Target view shaping + deterministic cited rationale ─────────────────────


def _edge_row(**kw) -> dict:
    base = dict(source_id="00000000-0000-0000-0000-000000000001", relation="confers_resistance",
                target_type="drug", target_id=None, target_literal="ciprofloxacin",
                confidence=0.9, grounded=True, provenance_pmid="222", provenance_db="CARD",
                provenance_acc="ARO:3003378", metadata={"subject": "MarR"},
                paper_title="T", paper_year=2021)
    base.update(kw)
    return base


def _target_row(**kw) -> dict:
    base = dict(id="00000000-0000-0000-0000-0000000000aa",
                gene_id="00000000-0000-0000-0000-000000000001",
                mechanism="Efflux regulation — MarR", rank_score=0.62,
                tractability={"source": "ChEMBL", "assessed": True, "has_target": False,
                              "queried_acc": "A0A0H3KEU2", "bucket": "novel"},
                pdb_ids=[], metadata={"locus_tag": "A8H40_RS07590", "name": "MarR",
                                      "product": "MarR family regulator", "wp": "WP_006410546.1",
                                      "score_components": {"flipper_support": 10, "n_edges": 2}},
                locus_tag="A8H40_RS07590", name="MarR", product="MarR family regulator",
                wp="WP_006410546.1")
    base.update(kw)
    return base


def test_deterministic_rationale_cites_real_ids_only():
    edges = [
        {"relation": "confers_resistance", "target": "ciprofloxacin", "confidence": 0.9,
         "grounded": True, "provenance": {"db": "CARD", "acc": "ARO:3003378", "pmid": "222"}},
        {"relation": "implicates", "target": "efflux pump regulation", "confidence": 0.8,
         "grounded": True, "provenance": {"db": "CARD", "acc": "ARO:3000718", "pmid": "111"}},
    ]
    target = {"locus_tag": "A8H40_RS07590", "name": "MarR", "rank_score": 0.62,
              "score_components": {"flipper_support": 10},
              "tractability": {"assessed": True, "has_target": False, "queried_acc": "A0A0H3KEU2"}}
    text_out, citations = deterministic_rationale(target, edges)
    assert "MarR" in text_out and "0.62" in text_out
    assert "CARD:ARO:3003378" in citations  # cites the real grounded accession
    assert "ChEMBL:A0A0H3KEU2" in citations  # novel-target tractability cited
    assert "flipper support 10" in text_out  # reversibility surfaced
    # No fabricated citation ids: every citation traces to an input edge or the acc.
    allowed = {"CARD:ARO:3003378", "CARD:ARO:3000718", "PMID:222", "PMID:111", "ChEMBL:A0A0H3KEU2"}
    assert set(citations) <= allowed


def test_shape_target_flags_strain_and_structure():
    v = shape_target(_target_row(), [_edge_row()], {"in_strain": True, "strain_flipper": True})
    assert v["locus_tag"] == "A8H40_RS07590"
    assert v["rank_score"] == 0.62
    assert v["in_strain"] is True and v["strain_flipper"] is True
    assert v["structure"]["available"] is True and v["structure"]["wp"] == "WP_006410546.1"
    assert v["evidence_counts"] == {"total": 1, "grounded": 1}
    assert v["rationale_source"] == "deterministic"
    assert v["rationale"] and v["rationale_citations"]


def test_shape_targets_sorts_by_rank_and_counts_structures():
    rows = [
        _target_row(id="a", gene_id="g1", rank_score=0.30, locus_tag="LOW",
                    metadata={"locus_tag": "LOW", "wp": None}, wp=None),
        _target_row(id="b", gene_id="g2", rank_score=0.62, locus_tag="HIGH",
                    metadata={"locus_tag": "HIGH", "wp": "WP_1"}, wp="WP_1"),
    ]
    edges = {"g1": [], "g2": [_edge_row(source_id="g2")]}
    out = shape_targets({"id": "s", "label": "167"}, "Burkholderia multivorans", rows, edges, {})
    assert [t["locus_tag"] for t in out["targets"]] == ["HIGH", "LOW"]  # rank desc
    assert out["counts"]["targets"] == 2
    assert out["counts"]["with_structure"] == 1


def test_chembl_summarize_and_bucket_are_honest_without_fabrication():
    # No target found → 'novel', assessed but has_target False, no invented accession.
    novel = chembl.summarize({"queried_acc": "X", "chembl_target_id": None})
    assert novel["assessed"] is True and novel["has_target"] is False
    assert novel["bucket"] == "novel"
    # A precedented target (known-drug mechanism) buckets above bare bioactivity.
    prec = chembl.summarize({
        "queried_acc": "Y", "chembl_target_id": "CHEMBL999",
        "n_bioactivities": 120, "n_compounds": 40,
        "mechanisms": [{"molecule_chembl_id": "CHEMBL25", "mechanism_of_action": "x"}],
    })
    assert prec["has_target"] is True and prec["bucket"] == "precedented"
    # Empty / None record → assessed False, nothing fabricated.
    assert chembl.summarize(None) == {"source": "ChEMBL", "assessed": False}
