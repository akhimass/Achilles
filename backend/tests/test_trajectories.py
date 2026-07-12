"""Slice 2 tests: deterministic trajectory RETRIEVAL. No DB, no network, no LLM, no
BurkData — a synthetic lineage fixture exercises the engine.

Locks the non-negotiable line: the engine only reports observed reality (with backing
strains + lineage support), never predicts/simulates/generates, and shows an honest
'insufficient real evidence' state when the data can't support an answer.
"""

from __future__ import annotations

from app.ingestion.trajectories import LineageResSens, retrieve_trajectory

ORG = "Test organism"

# Synthetic record: MEM→SXT in two lineages; MEM→CAZ in one; a self-pair to drop;
# LVX→MEM elsewhere (should not appear when we query MEM as the resisted drug).
FIXTURE = [
    LineageResSens("2", ["L1"], ["MEM"], ["SXT"]),
    LineageResSens("10", ["L2"], ["MEM"], ["SXT", "CAZ"]),
    LineageResSens("167", ["L2"], ["MEM"], ["CAZ"]),
    LineageResSens("9", ["L1"], ["MEM"], ["MEM"]),      # self-pair → dropped
    LineageResSens("30", ["L3"], ["LVX"], ["MEM"]),      # different resisted drug
    LineageResSens("40", ["L1"], ["SXT"], ["MEM"]),      # reverse of MEM→SXT (reciprocal)
]


def test_retrieves_observed_next_with_support_and_backing():
    t = retrieve_trajectory(FIXTURE, "MEM", organism=ORG)
    assert t.sufficient is True and t.kind == "retrieved"
    drugs = {o.sensitized_to: o for o in t.observed_next}
    assert set(drugs) == {"SXT", "CAZ"}  # MEM self-pair excluded
    sxt = drugs["SXT"]
    assert sxt.n_lineages == 2 and sxt.n_strains == 2
    assert sxt.backing_strains == ["2", "10"]  # natural (numeric) sort
    assert sorted(sxt.lineages) == ["L1", "L2"]
    caz = drugs["CAZ"]
    assert caz.n_lineages == 1 and caz.backing_strains == ["10", "167"]
    # SXT (2 lineages) ranks before CAZ (1 lineage).
    assert [o.sensitized_to for o in t.observed_next] == ["SXT", "CAZ"]
    # Aggregate backing + support.
    assert t.backing_strains == ["2", "9", "10", "167"]
    assert t.support_lineages == 2  # L1, L2


def test_reciprocal_reversions_are_flagged_for_cycling():
    # MEM→SXT and SXT→MEM are both observed → SXT is reciprocal (cycle-eligible).
    # MEM→CAZ is observed but CAZ→MEM is not → CAZ is not reciprocal.
    t = retrieve_trajectory(FIXTURE, "MEM", organism=ORG)
    drugs = {o.sensitized_to: o for o in t.observed_next}
    assert drugs["SXT"].reciprocal is True
    assert drugs["CAZ"].reciprocal is False
    assert t.reciprocal_count == 1


def test_retrieval_is_input_order_independent():
    a = retrieve_trajectory(FIXTURE, "MEM", organism=ORG)
    b = retrieve_trajectory(list(reversed(FIXTURE)), "MEM", organism=ORG)
    assert [(o.sensitized_to, o.n_lineages, o.backing_strains) for o in a.observed_next] == [
        (o.sensitized_to, o.n_lineages, o.backing_strains) for o in b.observed_next
    ]


def test_no_backing_event_is_insufficient_not_fabricated():
    t = retrieve_trajectory(FIXTURE, "ZZZ", organism=ORG)
    assert t.sufficient is False
    assert t.observed_next == [] and t.backing_strains == []
    assert "no real trajectory" in (t.note or "").lower()
    assert t.kind == "retrieved"


def test_resistance_without_collateral_is_insufficient():
    recs = [LineageResSens("1", ["L1"], ["MEM"], [])]  # resisted, but no sensitivity
    t = retrieve_trajectory(recs, "MEM", organism=ORG)
    assert t.sufficient is False and t.observed_next == []
    assert t.backing_strains == ["1"]  # the event is real...
    assert "no collateral sensitivity" in (t.note or "").lower()  # ...but nothing followed


def test_provenance_declares_no_prediction():
    t = retrieve_trajectory(FIXTURE, "MEM", organism=ORG, event_strain="10")
    assert t.event_strain == "10"
    assert "no prediction" in t.provenance["method"]
    assert "simulation" in t.provenance["method"] or "generation" in t.provenance["method"]


# ─── Router helper + cache reader (Slice 3) ──────────────────────────────────


def test_as_list_handles_list_json_and_none():
    from app.routers.trajectory import _as_list

    assert _as_list(["MEM", "SXT"]) == ["MEM", "SXT"]
    assert _as_list('["MEM", "SXT"]') == ["MEM", "SXT"]  # jsonb-as-string path
    assert _as_list(None) == [] and _as_list("not json") == []


def test_trajectory_cache_reader(tmp_path, monkeypatch):
    import json as _json

    from app.ai import narration_cache

    tf = tmp_path / "trajectory.json"
    tf.write_text(_json.dumps({
        "Burkholderia multivorans|MEM": {
            "summary": "In 3 real lineages, meropenem resistance was followed by SXT sensitivity.",
            "citations": ["strain 183", "strain 555"], "model": "claude-opus-4-8",
        }
    }))
    monkeypatch.setattr(narration_cache, "TRAJECTORY_FILE", tf)
    narration_cache.reset_cache()
    entry = narration_cache.trajectory_narrative("Burkholderia multivorans", "MEM")
    assert entry and entry["summary"].startswith("In 3 real lineages")
    assert narration_cache.trajectory_narrative("Burkholderia multivorans", "NOPE") is None
    # An entry without a summary is treated as absent (never served as fabricated).
    tf.write_text(_json.dumps({"O|D": {"citations": ["x"]}}))
    narration_cache.reset_cache()
    assert narration_cache.trajectory_narrative("O", "D") is None
