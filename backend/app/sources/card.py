"""CARD adapter — the resistance-gene -> mechanism -> drug-class truth layer.

Used by grounding.py to corroborate extracted claims. CARD's Antibiotic Resistance
Ontology (ARO) is queried through EBI OLS (public), returning compact quotable fact
blocks that carry the ARO accession so it can become edge provenance
(provenance_db='CARD', provenance_acc='ARO:...'). Results are cached under
data/demo/reference/ (committed, public) for offline reproducibility.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.sources import _refcache


async def lookup(subject: str, obj: str, organism: str) -> str | None:
    """Return corroborating CARD/ARO facts for (subject, object) or None."""
    key = f"{subject}|{obj}"
    cached = _refcache.load("card", key)
    if cached is not None:
        return cached.get("block") or None

    facts: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for q in [t for t in (subject, obj) if t and t.strip()]:
            try:
                r = await client.get(
                    f"{settings.ols_base}/search",
                    params={"q": q, "ontology": "aro", "rows": 4},
                )
            except httpx.HTTPError:
                continue
            if r.status_code != 200:
                continue
            for doc in (r.json().get("response") or {}).get("docs", []):
                acc = doc.get("obo_id")
                if not acc or not str(acc).startswith("ARO"):
                    continue
                desc = doc.get("description")
                if isinstance(desc, list):
                    desc = desc[0] if desc else None
                facts.append({"acc": acc, "label": doc.get("label"), "desc": desc})

    # Dedupe by accession, keep a small block.
    seen: set[str] = set()
    uniq: list[dict] = []
    for f in facts:
        if f["acc"] in seen:
            continue
        seen.add(f["acc"])
        uniq.append(f)
    uniq = uniq[:5]

    block = (
        "\n".join(
            f"CARD/ARO {f['acc']} — {f['label']}" + (f": {f['desc']}" if f.get("desc") else "")
            for f in uniq
        )
        or None
    )
    _refcache.save("card", key, {"subject": subject, "object": obj, "facts": uniq, "block": block})
    return block
