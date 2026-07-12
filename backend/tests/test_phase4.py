"""Phase 4 tests: deterministic collateral-sensitivity seeding + cycle shaping.

No DB, no network, no LLM, and no dependency on the private BurkData snapshot — a
small synthetic resistance/sensitivity record exercises the transform. These lock the
rule that the cycle is computed, not invented, and that the LLM never reorders it.
"""

from __future__ import annotations

from app.ingestion.collateral import propose_cycle
from app.ingestion.seed_collateral import build_collateral_pairs, observations_from_res_sens
from app.treatment_shaping import shape_cycle


# Synthetic per-lineage record: MEM<->SXT reciprocal across two lineages; a dangling
# CAZ->CHL with no return edge; a self-pair that must be dropped.
_RES_SENS = {
    "f1": {"resistance": ["MEM"], "sensitivity": ["SXT"]},   # L1: MEM -> SXT
    "c1": {"resistance": ["SXT"], "sensitivity": ["MEM"]},   # L1: SXT -> MEM (reciprocal)
    "f2": {"resistance": ["MEM"], "sensitivity": ["SXT"]},   # L2: MEM -> SXT (2nd lineage)
    "c2": {"resistance": ["SXT"], "sensitivity": ["MEM"]},   # L2: SXT -> MEM
    "c3": {"resistance": ["CAZ"], "sensitivity": ["CHL"]},   # L1: CAZ -> CHL (no return)
    "c4": {"resistance": ["MIN"], "sensitivity": ["MIN"]},   # self-pair -> dropped
    "c5": {"resistance": [], "sensitivity": ["MEM"]},        # no resistance -> no obs
}
_LINEAGES = {"f1": ["L1"], "c1": ["L1"], "f2": ["L2"], "c2": ["L2"], "c3": ["L1"],
             "c4": ["L1"], "c5": ["L1"]}


def test_observations_drop_self_pairs_and_empty_sides():
    obs = observations_from_res_sens(_RES_SENS, _LINEAGES)
    keys = {(o.lineage_id, o.resisted, o.sensitized) for o in obs}
    assert ("L1", "MEM", "SXT") in keys and ("L1", "SXT", "MEM") in keys
    assert ("L2", "MEM", "SXT") in keys
    assert ("L1", "CAZ", "CHL") in keys
    assert not any(o.resisted == o.sensitized for o in obs)  # self-pair dropped
    assert not any(o.lineage_id == "L1" and o.resisted == "MIN" for o in obs)  # c4 dropped


def test_observations_are_deterministic_order():
    a = observations_from_res_sens(_RES_SENS, _LINEAGES)
    b = observations_from_res_sens(dict(reversed(list(_RES_SENS.items()))), _LINEAGES)
    key = lambda o: (o.lineage_id, o.resisted, o.sensitized)
    assert [key(o) for o in a] == [key(o) for o in b]  # order-independent


def test_reciprocal_detection_and_cycle_from_pairs():
    pairs = build_collateral_pairs({"res_sens": _RES_SENS, "strain_lineages": _LINEAGES}, "Test org")
    recip = {(p.drug_a, p.drug_b) for p in pairs if p.reciprocal}
    assert ("MEM", "SXT") in recip and ("SXT", "MEM") in recip  # reciprocal both ways
    # CAZ->CHL has no return edge, so it is NOT reciprocal.
    assert not any(p.reciprocal and {p.drug_a, p.drug_b} == {"CAZ", "CHL"} for p in pairs)
    # MEM<->SXT is supported by 2 lineages.
    mem_sxt = next(p for p in pairs if (p.drug_a, p.drug_b) == ("MEM", "SXT"))
    assert mem_sxt.n_lineages == 2
    cycle = propose_cycle(pairs)
    assert set(cycle) == {"MEM", "SXT"} and len(cycle) == 2  # the only RCS loop


def test_empty_snapshot_yields_no_pairs():
    assert build_collateral_pairs({"res_sens": {}, "strain_lineages": {}}) == []


def test_shape_cycle_labels_hypothesis_and_orders_pairs():
    pairs = build_collateral_pairs({"res_sens": _RES_SENS, "strain_lineages": _LINEAGES}, "Test org")
    cycle = propose_cycle(pairs)
    out = shape_cycle("Test org", cycle, pairs, narrative=None)
    assert out["organism"] == "Test org"
    assert out["cycle"] == cycle
    assert out["is_hypothesis"] is True  # always flagged a research hypothesis
    assert out["steps"] and out["steps"][0]["from"] == cycle[0]
    # Reciprocal pairs surfaced, strongest (most lineages) first.
    assert out["rcs_pairs"] and out["rcs_pairs"][0]["n_lineages"] >= out["rcs_pairs"][-1]["n_lineages"]
    assert out["counts"]["reciprocal"] >= 1
