"""Reader + shaper for the docking / druggability beat (network-free).

Starts from a cited known inhibitor per target (data/demo/docking/ligands.json), and
serves any Tamarind results that have been computed and cached under
data/demo/docking/results/ — ADMET drug-property predictions and a docking pose/score
into the AlphaFold structure. Deterministic file reads; the live Tamarind runs happen
in app/sources/dock.py. Public ligands only.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DOCKING_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "docking"
LIGANDS_FILE = DOCKING_DIR / "ligands.json"
RESULTS_DIR = DOCKING_DIR / "results"


@lru_cache(maxsize=1)
def _ligands() -> dict:
    try:
        return json.loads(LIGANDS_FILE.read_text()).get("ligands", {})
    except (ValueError, OSError):
        return {}


def load_ligands() -> dict:
    return dict(_ligands())


def load_result(locus: str) -> dict | None:
    f = RESULTS_DIR / f"{locus}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except (ValueError, OSError):
        return None


def reset_cache() -> None:
    _ligands.cache_clear()


def _pubchem_url(cid) -> str | None:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else None


def shape_docking(locus: str, ligands: list[dict], result: dict | None) -> dict:
    """Assemble the /api/docking view for one target. Pure and deterministic.

    `status`: 'docked' (pose available), 'properties_only' (ADMET computed, no pose),
    or 'ready' (cited ligand known, Tamarind run pending). Never fabricated — a pose or
    ADMET value only appears when a real Tamarind result was cached.
    """
    lig_views = [
        {
            "name": l.get("name"),
            "smiles": l.get("smiles"),
            "pubchem_cid": l.get("pubchem_cid"),
            "pubchem_url": _pubchem_url(l.get("pubchem_cid")),
            "role": l.get("role"),
            "citation": l.get("citation"),
            "note": l.get("note"),
        }
        for l in ligands
    ]
    admet = (result or {}).get("admet")
    docking = (result or {}).get("docking")
    if docking and docking.get("pose_available"):
        status = "docked"
    elif admet:
        status = "properties_only"
    else:
        status = "ready"
    return {
        "locus": locus,
        "ligands": lig_views,
        "admet": admet,
        "docking": docking,
        "status": status,
        "runner": "Tamarind Bio (ADMET + docking)",
    }


def shape_all() -> dict:
    """All targets with a cited ligand, with any cached Tamarind results."""
    out = [shape_docking(locus, ligs, load_result(locus)) for locus, ligs in _ligands().items()]
    return {"targets": out, "counts": {"with_ligand": len(out),
                                       "docked": sum(1 for t in out if t["status"] == "docked")}}
