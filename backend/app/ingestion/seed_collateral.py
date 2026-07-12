"""Seed `collateral_sensitivity` from the per-lineage resistance/sensitivity record.

Deterministic and network-free. Reads the experimental resistance/sensitivity data
in the demo snapshot (real BurkData locally; the public path simply yields nothing if
that field is absent) and turns it into collateral-sensitivity pairs via the already-
tested `ingestion/collateral.py` math. No LLM: the cycle is computed, then narrated
elsewhere.

Data rights: the resistance/sensitivity table is derived from the private BurkData
snapshot, so the resulting `collateral_sensitivity` rows are LOCAL-ONLY. Nothing here
is committed; a public clone (no BurkData) seeds no collateral rows and the treatment
endpoint degrades gracefully to an empty state.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.collateral import (
    CollateralPair,
    SensitivityObservation,
    compute_collateral_pairs,
)

_DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"
SNAPSHOT_BURK = _DEMO / "bmultivorans_burkdata.json"
SNAPSHOT_PUBLIC = _DEMO / "bmultivorans_pubmlst.json"
ORGANISM = "Burkholderia multivorans"


def observations_from_res_sens(
    res_sens: dict[str, dict], strain_lineages: dict[str, list[str]]
) -> list[SensitivityObservation]:
    """Turn per-strain resistance/sensitivity + lineage membership into observations.

    Pure and deterministic. For a clone that acquired resistance to drug A while being
    sensitive to drug B, we record (lineage, A, B) — one observation per lineage the
    clone belongs to, so the reciprocal-CS aggregation counts *distinct lineages*
    supporting each directed pair (never inflating support by counting clones twice
    within a lineage; `compute_collateral_pairs` de-dups by lineage id).

    Output is sorted for determinism (same snapshot → identical observation list).
    """
    obs: list[SensitivityObservation] = []
    for strain, rs in res_sens.items():
        resisted = rs.get("resistance") or []
        sensitized = rs.get("sensitivity") or []
        if not resisted or not sensitized:
            continue
        lineages = strain_lineages.get(strain) or []
        for lineage in lineages:
            for a in resisted:
                for b in sensitized:
                    if a == b:
                        continue  # a drug can't sensitize to itself
                    obs.append(SensitivityObservation(lineage_id=lineage, resisted=a, sensitized=b))
    obs.sort(key=lambda o: (o.lineage_id, o.resisted, o.sensitized))
    return obs


def build_collateral_pairs(snapshot: dict, organism: str = ORGANISM) -> list[CollateralPair]:
    """Snapshot → collateral-sensitivity pairs (pure). Empty if no res/sens present."""
    res_sens = snapshot.get("res_sens") or {}
    strain_lineages = snapshot.get("strain_lineages") or {}
    if not res_sens:
        return []
    observations = observations_from_res_sens(res_sens, strain_lineages)
    return compute_collateral_pairs(observations, organism, min_lineages=1)


def _load_snapshot() -> dict | None:
    for path in (SNAPSHOT_BURK, SNAPSHOT_PUBLIC):
        if path.exists():
            data = json.loads(path.read_text())
            if data.get("res_sens"):
                return data
    return None


async def seed_collateral(organism: str = ORGANISM) -> dict:
    """Compute collateral pairs from the snapshot and upsert `collateral_sensitivity`."""
    from sqlalchemy import text

    from app.db import SessionLocal

    snapshot = _load_snapshot()
    if snapshot is None:
        print("seed(collateral): skipped — no resistance/sensitivity data in snapshot")
        return {"pairs": 0, "reciprocal": 0}

    pairs = build_collateral_pairs(snapshot, organism)
    if pairs:
        async with SessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO collateral_sensitivity
                          (organism, drug_a, drug_b, reciprocal, strength, n_lineages, metadata)
                        VALUES (:organism, :drug_a, :drug_b, :reciprocal, :strength, :n_lineages,
                                CAST(:metadata AS jsonb))
                        ON CONFLICT (organism, drug_a, drug_b) DO UPDATE
                          SET reciprocal = EXCLUDED.reciprocal, strength = EXCLUDED.strength,
                              n_lineages = EXCLUDED.n_lineages, metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "organism": p.organism,
                            "drug_a": p.drug_a,
                            "drug_b": p.drug_b,
                            "reciprocal": p.reciprocal,
                            "strength": p.strength,
                            "n_lineages": p.n_lineages,
                            "metadata": json.dumps(p.metadata),
                        }
                        for p in pairs
                    ],
                )
    reciprocal = sum(1 for p in pairs if p.reciprocal)
    print(
        f"seed(collateral): {len(pairs)} collateral-sensitivity pairs "
        f"({reciprocal} reciprocal) — {organism} (BurkData, local)"
    )
    return {"pairs": len(pairs), "reciprocal": reciprocal}
