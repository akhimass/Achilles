"""Europe PMC adapter — fetch abstracts for a scoped literature corpus.

Public REST API, no key required. The corpus is deliberately SCOPED (one organism's
resistance literature, keyed per target gene/mechanism) — never open-ended. Raw
responses are cached by the snapshot builder so seeding and the demo run offline.

`hit_to_paper` is a pure mapping (unit-tested); `search` does the paging I/O.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.models.domain import Paper


def hit_to_paper(hit: dict) -> Paper | None:
    """Map one Europe PMC `core` result to a Paper. Returns None if it lacks the
    minimum for evidence work: a PMID (provenance) and an abstract (to extract from)."""
    pmid = hit.get("pmid") or hit.get("pmcid")
    abstract = hit.get("abstractText")
    title = hit.get("title")
    if not pmid or not abstract or not title:
        return None
    year = None
    if hit.get("pubYear"):
        try:
            year = int(hit["pubYear"])
        except (ValueError, TypeError):
            year = None
    return Paper(
        pmid=str(pmid),
        doi=hit.get("doi"),
        title=title.strip().rstrip("."),
        abstract=abstract.strip(),
        year=year,
        source="europepmc",
        metadata={"authorString": hit.get("authorString"), "journal": hit.get("journalTitle")},
    )


async def fetch_raw(query: str, *, limit: int = 40) -> list[dict]:
    """Page Europe PMC (resultType=core, cursorMark) and return raw result dicts.

    Separated from mapping so the snapshot builder can cache the raw JSON verbatim.
    """
    results: list[dict] = []
    cursor = "*"
    page_size = min(100, limit)
    async with httpx.AsyncClient(timeout=40) as client:
        while len(results) < limit:
            resp = await client.get(
                f"{settings.europepmc_base}/search",
                params={
                    "query": query,
                    "resultType": "core",
                    "format": "json",
                    "pageSize": page_size,
                    "cursorMark": cursor,
                },
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            batch = (data.get("resultList") or {}).get("result") or []
            results.extend(batch)
            next_cursor = data.get("nextCursorMark")
            if not batch or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
    return results[:limit]


async def search(query: str, *, limit: int = 40) -> list[Paper]:
    """Search Europe PMC and return Papers with abstracts (title + abstract + pmid)."""
    raw = await fetch_raw(query, limit=limit)
    papers = [hit_to_paper(h) for h in raw]
    return [p for p in papers if p is not None]
