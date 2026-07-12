"""PubMLST adapter — real per-isolate MLST genotypes + provenance (public).

Why this source exists alongside BV-BRC: BV-BRC (see `bvbrc.py`) supplies genome
metadata but not a clean, joinable per-isolate genotype. PubMLST's *Burkholderia
cepacia complex* database gives, for each real isolate, a 7-locus MLST allele
profile plus collection metadata (year, country, source) and PubMed citations —
exactly the discrete, per-strain signal Phase 1 needs to detect flippers over a
lineage. It is public (Jolley et al., pubmlst.org) and its REST API is stable.

This module only *fetches* (network lives in `sources/`). Everything downstream —
lineage reconstruction, flipper detection — is deterministic and network-free in
`ingestion/`. Raw responses are cached under `data/pubmlst/` so repeat runs are
offline and byte-reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

# BCC = Burkholderia cepacia complex; B. multivorans is genomovar II within it.
BCC_ISOLATES_DB = "https://rest.pubmlst.org/db/pubmlst_bcc_isolates"

# The seven MLST housekeeping loci for the BCC scheme, in canonical order.
MLST_LOCI: tuple[str, ...] = ("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB")


def _cache_dir() -> Path:
    # backend/app/sources/pubmlst.py -> repo/data/pubmlst
    root = Path(__file__).resolve().parents[3]
    d = root / "data" / "pubmlst"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _normalize(provenance: dict, st: int | None, pmids: list[str], profile: dict) -> dict:
    """One isolate -> the flat record shape the ingestion layer consumes."""
    return {
        "id": provenance["id"],
        "isolate": provenance.get("isolate"),
        "st": st,
        "year": provenance.get("year"),
        "country": provenance.get("country"),
        "continent": provenance.get("continent"),
        "source": provenance.get("source"),
        "detail": provenance.get("detail_of_isolation"),
        "ncbi": provenance.get("NCBI_assembly_accession"),
        "pmids": pmids,
        "profile": profile,
    }


async def fetch_isolates(
    organism: str = "Burkholderia multivorans",
    *,
    limit: int = 70,
    scan: int = 200,
    isolates_db: str = BCC_ISOLATES_DB,
    loci: tuple[str, ...] = MLST_LOCI,
) -> list[dict]:
    """Fetch complete, dated isolates for `organism` from a PubMLST isolates database.

    Real HTTP via httpx. Keeps only isolates with a full MLST profile (all `loci`) and a
    collection year + country (so the lineage/flipper stages have real signal).
    Deterministic: isolates are scanned in ascending id order and the first `limit`
    complete ones are returned. Raw per-isolate JSON is cached under data/pubmlst/.

    `isolates_db` + `loci` come from the domain registry (app/ingestion/domains.py), so
    the SAME fetch path serves any configured organism — Burkholderia is just the default.
    """
    cache = _cache_dir()
    async with httpx.AsyncClient(timeout=90) as client:
        urls = await _search_isolate_urls(client, organism, cap=scan, cache=cache, db=isolates_db)
        records: list[dict] = []
        for url in urls:
            rec = await _fetch_one(client, url, cache, db=isolates_db, loci=loci)
            if rec is None:
                continue
            records.append(rec)
            if len(records) >= limit:
                break
    return records


async def fetch_domain_isolates(domain, *, limit: int = 70, scan: int = 200) -> list[dict]:
    """Fetch isolates for a DomainConfig (uses its PubMLST db + MLST scheme)."""
    return await fetch_isolates(
        domain.organism, limit=limit, scan=scan,
        isolates_db=domain.pubmlst_isolates_db, loci=tuple(domain.mlst_loci),
    )


async def _search_isolate_urls(
    client: httpx.AsyncClient, organism: str, *, cap: int, cache: Path, db: str = BCC_ISOLATES_DB
) -> list[str]:
    urls: list[str] = []
    resp = await client.post(f"{db}/isolates/search", json={"field.species": organism})
    resp.raise_for_status()
    data = resp.json()
    urls.extend(data.get("isolates", []))
    while data.get("paging", {}).get("next") and len(urls) < cap:
        resp = await client.get(data["paging"]["next"])
        resp.raise_for_status()
        data = resp.json()
        urls.extend(data.get("isolates", []))
    return urls[:cap]


async def _fetch_one(
    client: httpx.AsyncClient, url: str, cache: Path,
    *, db: str = BCC_ISOLATES_DB, loci: tuple[str, ...] = MLST_LOCI,
) -> dict | None:
    isolate_id = url.rstrip("/").rsplit("/", 1)[-1]
    cached = cache / f"isolate_{isolate_id}.json"
    if cached.exists():
        raw = json.loads(cached.read_text())
    else:
        rec = (await client.get(url)).json()
        alleles = (await client.get(f"{db}/isolates/{isolate_id}/allele_ids")).json()
        raw = {"record": rec, "alleles": alleles}
        cached.write_text(json.dumps(raw))

    rec, alleles = raw["record"], raw["alleles"]
    provenance = rec.get("provenance", {})
    st = None
    for scheme in rec.get("schemes", []):
        if scheme.get("description") == "MLST":
            st = scheme.get("fields", {}).get("ST")
    pmids = [str(p["pubmed_id"]) for p in rec.get("publications", []) if p.get("pubmed_id")]

    profile: dict[str, int] = {}
    for item in alleles.get("allele_ids", []):
        for locus, allele in item.items():
            if isinstance(allele, int):
                profile[locus] = allele

    if len(profile) != len(loci):
        return None
    if not provenance.get("year") or not provenance.get("country"):
        return None
    return _normalize(provenance, st, pmids, profile)


def build_snapshot(records: list[dict], organism: str) -> dict:
    """Wrap fetched records with a provenance manifest for the committed demo file."""
    return {
        "meta": {
            "organism": organism,
            "n_isolates": len(records),
            "loci": list(MLST_LOCI),
            "provenance": "PubMLST — Burkholderia cepacia complex isolates database",
            "source_url": BCC_ISOLATES_DB,
            "citation": "Jolley KA, Bray JE, Maiden MCJ (2018), pubmlst.org (public).",
            "note": (
                "Real isolates + real MLST allele profiles. Collection metadata is "
                "used only to reconstruct a lineage deterministically (see "
                "ingestion/lineage.py); it is not a validated phylogeny."
            ),
        },
        "records": records,
    }
