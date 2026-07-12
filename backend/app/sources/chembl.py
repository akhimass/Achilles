"""ChEMBL adapter — tractability evidence for a candidate target.

Given a target protein's UniProt accession, ask the public ChEMBL API whether any
chemical matter is known against it: is there a ChEMBL target, how many bioactivities
with a measured pChEMBL, how many distinct compounds, and any approved/known drugs
via the mechanism endpoint. That is exactly the "is this druggable / has anyone made
a molecule for it" signal Phase 3 wants for `targets.tractability`.

Two access modes, mirroring the rest of `sources/`:
  - `lookup(acc)` — cache-first, then the live public API; result cached under
    data/demo/reference/ (public, committed) so the demo reproduces offline.
  - `tractability_from_cache(acc)` — cache-only, network-free; used by the
    deterministic seed so ingestion never touches the network.

We never invent an accession or a bioactivity count. If ChEMBL has nothing for the
accession, that is recorded faithfully (`has_target=False`) — a real, informative
"no known chemical matter / novel target" signal, not a fabricated one.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.sources import _refcache

CHEMBL_BASE = getattr(settings, "chembl_base", "https://www.ebi.ac.uk/chembl/api/data")
_MAX_INHIBITORS = 5


def _bucket(has_target: bool, n_bioactivities: int, n_mechanisms: int) -> str:
    """Coarse, deterministic tractability label from the ChEMBL counts."""
    if not has_target:
        return "novel"  # no ChEMBL target maps here — no known chemical matter
    if n_mechanisms > 0:
        return "precedented"  # an approved/known drug acts via this target
    if n_bioactivities >= 50:
        return "well-explored"
    if n_bioactivities > 0:
        return "some-chemical-matter"
    return "target-only"  # ChEMBL knows the target but no bioactivity recorded


def summarize(record: dict | None) -> dict:
    """Shape a raw ChEMBL record into the compact tractability block we persist.

    Pure: safe to call on cache contents. Always returns a dict with `assessed`.
    """
    if not record:
        return {"source": "ChEMBL", "assessed": False}
    has_target = bool(record.get("chembl_target_id"))
    n_bio = int(record.get("n_bioactivities") or 0)
    mechs = record.get("mechanisms") or []
    n_mech = len(mechs)
    return {
        "source": "ChEMBL",
        "assessed": True,
        "queried_acc": record.get("queried_acc"),
        "has_target": has_target,
        "chembl_target_id": record.get("chembl_target_id"),
        "target_pref_name": record.get("target_pref_name"),
        "target_organism": record.get("target_organism"),
        "n_bioactivities": n_bio,
        "n_compounds": int(record.get("n_compounds") or 0),
        "max_pchembl": record.get("max_pchembl"),
        "mechanisms": mechs[:_MAX_INHIBITORS],
        "known_inhibitors": (record.get("known_inhibitors") or [])[:_MAX_INHIBITORS],
        "bucket": _bucket(has_target, n_bio, n_mech),
        "note": record.get("note"),
    }


def tractability_from_cache(acc: str | None) -> dict:
    """Cache-only, network-free tractability for the deterministic seed.

    Returns an `assessed=False` block if no cache exists yet (honest — nothing is
    fabricated), so the offline public path still seeds without a network fetch.
    """
    if not acc:
        return {"source": "ChEMBL", "assessed": False}
    cached = _refcache.load("chembl", acc)
    return summarize((cached or {}).get("record"))


async def _get_json(client: httpx.AsyncClient, path: str, params: dict) -> dict | None:
    try:
        r = await client.get(f"{CHEMBL_BASE}/{path}", params=params)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


async def _fetch(acc: str) -> dict | None:
    """Live ChEMBL fetch for one UniProt accession. Returns a raw record or None."""
    async with httpx.AsyncClient(timeout=30, headers={"Accept": "application/json"}) as client:
        targets = await _get_json(
            client, "target.json",
            {"target_components__accession": acc, "limit": 5},
        )
        tlist = (targets or {}).get("targets") or []
        # Prefer a SINGLE PROTEIN target if present, else the first.
        single = [t for t in tlist if t.get("target_type") == "SINGLE PROTEIN"]
        tgt = (single or tlist or [None])[0]
        if not tgt:
            return {
                "queried_acc": acc, "chembl_target_id": None,
                "note": "No ChEMBL target maps to this UniProt accession.",
            }
        tid = tgt.get("target_chembl_id")

        acts = await _get_json(
            client, "activity.json",
            {"target_chembl_id": tid, "pchembl_value__isnull": "false",
             "limit": _MAX_INHIBITORS, "order_by": "-pchembl_value"},
        )
        activities = (acts or {}).get("activities") or []
        total = (((acts or {}).get("page_meta") or {}).get("total_count")) or len(activities)
        top = [
            {
                "molecule_chembl_id": a.get("molecule_chembl_id"),
                "pchembl_value": a.get("pchembl_value"),
                "standard_type": a.get("standard_type"),
            }
            for a in activities
            if a.get("molecule_chembl_id")
        ]
        max_p = None
        for a in activities:
            try:
                p = float(a.get("pchembl_value"))
            except (TypeError, ValueError):
                continue
            max_p = p if max_p is None else max(max_p, p)

        mech = await _get_json(client, "mechanism.json", {"target_chembl_id": tid, "limit": 10})
        mechanisms = [
            {
                "molecule_chembl_id": m.get("molecule_chembl_id"),
                "mechanism_of_action": m.get("mechanism_of_action"),
                "action_type": m.get("action_type"),
            }
            for m in ((mech or {}).get("mechanisms") or [])
            if m.get("molecule_chembl_id")
        ]

        return {
            "queried_acc": acc,
            "chembl_target_id": tid,
            "target_pref_name": tgt.get("pref_name"),
            "target_organism": tgt.get("organism"),
            "n_bioactivities": int(total),
            "n_compounds": len({t["molecule_chembl_id"] for t in top}),
            "max_pchembl": max_p,
            "known_inhibitors": top,
            "mechanisms": mechanisms,
            "note": None,
        }


async def lookup(acc: str, *, use_cache: bool = True) -> dict:
    """Tractability for a UniProt accession: cache-first, then the live ChEMBL API.

    The returned block is the compact, persisted shape (see `summarize`). The raw
    record is cached under data/demo/reference/ so the demo reproduces offline.
    """
    if not acc:
        return {"source": "ChEMBL", "assessed": False}
    if use_cache:
        cached = _refcache.load("chembl", acc)
        if cached is not None:
            return summarize(cached.get("record"))
    record = await _fetch(acc)
    _refcache.save("chembl", acc, {"acc": acc, "record": record})
    return summarize(record)


def build_reference_block(data: dict) -> str | None:
    """One-line human summary of a tractability block (for narration/UI hover)."""
    if not data or not data.get("assessed"):
        return None
    if not data.get("has_target"):
        return f"ChEMBL: no target for {data.get('queried_acc')} — no known chemical matter (novel)."
    parts = [f"ChEMBL {data.get('chembl_target_id')}"]
    if data.get("n_bioactivities"):
        parts.append(f"{data['n_bioactivities']} bioactivities")
    if data.get("n_compounds"):
        parts.append(f"{data['n_compounds']} compounds")
    if data.get("max_pchembl") is not None:
        parts.append(f"max pChEMBL {data['max_pchembl']}")
    if data.get("mechanisms"):
        parts.append(f"{len(data['mechanisms'])} known-drug mechanism(s)")
    return " · ".join(parts)
