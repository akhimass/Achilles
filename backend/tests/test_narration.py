"""Slice 1 tests: pre-reviewed narration cache read + merge. No DB, no network, no LLM.

Locks the rules: an empty cache leaves the deterministic rationale untouched (never
fabricated), a populated cache is served with its citations and labelled 'cached', and
the cycle payload honestly records its narration source.
"""

from __future__ import annotations

import json

from app.ai import narration_cache
from app.ingestion.collateral import CollateralPair
from app.targets_shaping import apply_cached_rationales
from app.treatment_shaping import shape_cycle


def _payload() -> dict:
    return {
        "targets": [
            {"locus_tag": "A8H40_RS07590", "rationale": "DET-A", "rationale_citations": ["PMID:1"],
             "rationale_source": "deterministic"},
            {"locus_tag": "A8H40_RS00780", "rationale": "DET-B", "rationale_citations": [],
             "rationale_source": "deterministic"},
        ]
    }


# ─── Reader (mocked cache files) ─────────────────────────────────────────────


def test_reader_returns_empty_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(narration_cache, "TARGETS_FILE", tmp_path / "nope.json")
    monkeypatch.setattr(narration_cache, "CYCLE_FILE", tmp_path / "nope2.json")
    narration_cache.reset_cache()
    assert narration_cache.load_target_rationales() == {}
    assert narration_cache.target_rationale("X") is None
    assert narration_cache.cycle_narrative("Y") is None


def test_reader_loads_committed_entries(tmp_path, monkeypatch):
    tf = tmp_path / "targets.json"
    tf.write_text(json.dumps({
        "A8H40_RS07590": {"narrative": "MarR is a strong target.", "citations": ["CARD:ARO:3003378"],
                          "model": "claude-opus-4-8", "generated_at": "2026-07-12T00:00:00+00:00"}
    }))
    monkeypatch.setattr(narration_cache, "TARGETS_FILE", tf)
    narration_cache.reset_cache()
    entry = narration_cache.target_rationale("A8H40_RS07590")
    assert entry and entry["narrative"].startswith("MarR")
    assert entry["citations"] == ["CARD:ARO:3003378"]
    # An entry without a narrative is treated as absent (never served as fabricated).
    tf.write_text(json.dumps({"L": {"citations": ["x"]}}))
    narration_cache.reset_cache()
    assert narration_cache.target_rationale("L") is None


def test_reader_tolerates_malformed_json(tmp_path, monkeypatch):
    tf = tmp_path / "targets.json"
    tf.write_text("{ not json")
    monkeypatch.setattr(narration_cache, "TARGETS_FILE", tf)
    narration_cache.reset_cache()
    assert narration_cache.load_target_rationales() == {}


# ─── Merge (pure) ────────────────────────────────────────────────────────────


def test_empty_cache_leaves_deterministic_untouched():
    p = _payload()
    apply_cached_rationales(p, {})
    assert p["targets"][0]["rationale"] == "DET-A"
    assert p["targets"][0]["rationale_source"] == "deterministic"


def test_cache_hit_replaces_and_labels_cached():
    p = _payload()
    cache = {"A8H40_RS07590": {"narrative": "Reviewed rationale.", "citations": ["CARD:ARO:3003378"],
                               "model": "claude-opus-4-8"}}
    apply_cached_rationales(p, cache)
    t0, t1 = p["targets"]
    assert t0["rationale"] == "Reviewed rationale."
    assert t0["rationale_source"] == "cached"
    assert t0["rationale_citations"] == ["CARD:ARO:3003378"]
    assert t0["rationale_model"] == "claude-opus-4-8"
    # Target with no cache entry keeps its deterministic rationale.
    assert t1["rationale"] == "DET-B" and t1["rationale_source"] == "deterministic"


def test_cache_entry_without_narrative_is_ignored():
    p = _payload()
    apply_cached_rationales(p, {"A8H40_RS07590": {"citations": ["x"]}})
    assert p["targets"][0]["rationale_source"] == "deterministic"  # not fabricated


# ─── Cycle narration source labelling ────────────────────────────────────────


def test_shape_cycle_labels_cached_narration_source():
    pairs = [CollateralPair(organism="O", drug_a="MEM", drug_b="SXT", reciprocal=True,
                            strength=0.1, n_lineages=3)]
    narr = {"summary": "Alternate MEM/SXT.", "caveats": ["hypothesis"], "citations": ["PMID:9"]}
    out = shape_cycle("O", ["MEM", "SXT"], pairs, narrative=narr, narrative_source="cached")
    assert out["narrative"]["source"] == "cached"
    assert out["narrative_source"] == "cached"
    assert out["summary"]  # deterministic summary still present
    # No narration → source is null, deterministic summary still there.
    out2 = shape_cycle("O", ["MEM", "SXT"], pairs, narrative=None)
    assert out2["narrative"] is None and out2["narrative_source"] is None
