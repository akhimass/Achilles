"""Tests for the docking/druggability shaping + result parsing. No DB/network/LLM.

Locks: the beat starts from a cited ligand, and a pose/ADMET value only appears when a
real Tamarind result is present (never fabricated); status reflects reality.
"""

from __future__ import annotations

from app.ai.docking_cache import shape_docking
from app.sources.dock import _parse_admet, _parse_docking

_LIG = [{"name": "CCCP", "smiles": "C1=CC(=CC(=C1)Cl)NN=C(C#N)C#N", "pubchem_cid": 2603,
         "role": "efflux inhibitor", "citation": "CARD:ARO:3000074", "note": "cited"}]


def test_ready_when_ligand_but_no_result():
    out = shape_docking("A8H40_RS19975", _LIG, None)
    assert out["status"] == "ready"
    lig = out["ligands"][0]
    assert lig["name"] == "CCCP" and lig["citation"] == "CARD:ARO:3000074"
    assert lig["pubchem_url"].endswith("/2603")
    assert out["admet"] is None and out["docking"] is None


def test_status_reflects_admet_then_dock():
    props = shape_docking("L", _LIG, {"admet": {"properties": {"logP": "2.1"}}})
    assert props["status"] == "properties_only" and props["admet"]["properties"]["logP"] == "2.1"
    docked = shape_docking("L", _LIG, {"admet": {"properties": {}},
                                       "docking": {"pose_available": True, "score": -7.2}})
    assert docked["status"] == "docked" and docked["docking"]["score"] == -7.2


def test_parse_admet_from_json_and_csv():
    j = _parse_admet({"admet_ai/results.json": b'{"logP": 2.1, "toxicity": 0.03}'})
    assert j["properties"]["logP"] == 2.1
    c = _parse_admet({"out.csv": b"logP,toxicity\n2.1,0.03\n"})
    assert c["properties"]["logP"] == "2.1"
    assert _parse_admet({"readme.txt": b"nope"}) is None


def test_parse_docking_finds_pose_and_score():
    d = _parse_docking({"rank1.pdb": b"ATOM...", "confidence.json": b'{"confidence": -6.5}'})
    assert d["pose_available"] is True and d["pose_file"] == "rank1.pdb"
    assert d["score"] == -6.5
    assert _parse_docking({"log.txt": b"no pose"}) is None
