"""UniProt adapter — protein identity for genes/targets and provenance accessions.

Queried through the public UniProt REST API; results cached under
data/demo/reference/ (committed, public). Returns a compact fact block carrying the
UniProt accession so grounding can attach provenance_db='UniProt'.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.sources import _refcache


def _protein_name(entry: dict) -> str | None:
    desc = entry.get("proteinDescription") or {}
    rec = (desc.get("recommendedName") or {}).get("fullName") or {}
    if rec.get("value"):
        return rec["value"]
    subs = desc.get("submissionNames") or []
    if subs:
        return (subs[0].get("fullName") or {}).get("value")
    return None


def _function(entry: dict) -> str | None:
    for c in entry.get("comments", []):
        if c.get("commentType") == "FUNCTION":
            texts = c.get("texts") or []
            if texts:
                return texts[0].get("value")
    return None


async def lookup(subject: str, organism: str) -> str | None:
    """Return a UniProt fact block for the subject protein, or None."""
    key = f"{subject}|{organism}"
    cached = _refcache.load("uniprot", key)
    if cached is not None:
        return cached.get("block") or None

    queries = [
        f"gene:{subject} AND organism_name:{organism}",
        f"protein_name:{subject} AND organism_name:{organism}",
        f"gene:{subject}",
    ]
    block: str | None = None
    record: dict | None = None
    async with httpx.AsyncClient(timeout=30) as client:
        for q in queries:
            try:
                r = await client.get(
                    f"{settings.uniprot_base}/uniprotkb/search",
                    params={
                        "query": q,
                        "fields": "accession,protein_name,cc_function,gene_names,organism_name",
                        "format": "json",
                        "size": 1,
                    },
                )
            except httpx.HTTPError:
                continue
            if r.status_code != 200:
                continue
            results = r.json().get("results", [])
            if not results:
                continue
            e = results[0]
            acc = e.get("primaryAccession")
            name = _protein_name(e)
            func = _function(e)
            org = (e.get("organism") or {}).get("scientificName")
            block = f"UniProt {acc} — {name or 'protein'} [{org}]" + (
                f"; function: {func}" if func else ""
            )
            record = {"acc": acc, "name": name, "function": func, "organism": org}
            break

    _refcache.save("uniprot", key, {"subject": subject, "organism": organism, "record": record, "block": block})
    return block
