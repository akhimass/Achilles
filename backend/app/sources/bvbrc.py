"""BV-BRC adapter — bacterial genomes and AMR phenotypes (public).

The strain supplier for ingestion. `fetch_strains` queries the public BV-BRC data
API (https://www.bv-brc.org/api) over real HTTP and maps genome records to typed
`Strain` rows. Raw responses are cached under `data/bvbrc/` so repeat runs are
offline and reproducible.

Note (build-time, 2026-07): the BV-BRC data API (Solr backend) was returning 503
during Phase 1 development, so the reproducible demo seeds from PubMLST instead
(see `pubmlst.py` and `ingestion/seed.py`). This adapter is the real BV-BRC path
for when the service is available; `_map_genome_record` is unit-tested against the
documented BV-BRC genome field shape so the mapping is verified regardless.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.config import settings
from app.models.domain import Strain

# BV-BRC genome fields we request (documented, stable field names).
_GENOME_FIELDS = (
    "genome_id,genome_name,strain,taxon_id,genome_status,genome_length,"
    "collection_year,collection_date,isolation_country,geographic_group,host_name"
)


def _cache_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
    d = root / "data" / "bvbrc"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _map_genome_record(rec: dict, organism: str) -> Strain:
    """Map one BV-BRC genome JSON record to a `Strain` (pure, deterministic).

    `external_id` is the BV-BRC genome_id; everything else that isn't a first-class
    Strain column is preserved under `metadata` so provenance is never lost.
    """
    label = rec.get("strain") or rec.get("genome_name") or str(rec.get("genome_id"))
    metadata = {
        "genome_name": rec.get("genome_name"),
        "taxon_id": rec.get("taxon_id"),
        "genome_status": rec.get("genome_status"),
        "genome_length": rec.get("genome_length"),
        "collection_year": rec.get("collection_year"),
        "collection_date": rec.get("collection_date"),
        "country": rec.get("isolation_country"),
        "geographic_group": rec.get("geographic_group"),
        "host_name": rec.get("host_name"),
    }
    return Strain(
        external_id=str(rec["genome_id"]),
        source="bvbrc",
        organism=organism,
        label=label,
        metadata={k: v for k, v in metadata.items() if v is not None},
    )


async def fetch_strains(organism: str, *, limit: int = 500) -> list[Strain]:
    """Fetch strains/isolates for an organism from BV-BRC and map to `Strain` rows.

    Real HTTP (POST RQL query) with a raw-response cache under data/bvbrc/. Raises a
    clear RuntimeError if the API is unreachable so callers can fall back to the
    committed demo snapshot.
    """
    cache = _cache_dir()
    slug = organism.lower().replace(" ", "_")
    cached = cache / f"genome_{slug}.json"

    if cached.exists():
        records = json.loads(cached.read_text())
    else:
        query = (
            f"eq(species,{organism})&select({_GENOME_FIELDS})"
            f"&sort(+genome_id)&limit({limit})"
        )
        headers = {
            "Content-Type": "application/rqlquery+x-www-form-urlencoded",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{settings.bvbrc_base}/genome/", content=query, headers=headers)
        if resp.status_code != 200 or not resp.text.lstrip().startswith("["):
            raise RuntimeError(
                f"BV-BRC genome query failed ({resp.status_code}); "
                f"the data API may be unavailable. Body: {resp.text[:160]}"
            )
        records = resp.json()
        cached.write_text(json.dumps(records))

    return [_map_genome_record(r, organism) for r in records]
