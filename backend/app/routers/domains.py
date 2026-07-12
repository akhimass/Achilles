"""Domains endpoint — the pipeline is domain-configurable, and says so.

`GET /api/domains` returns the registered domains and, honestly, whether each can seed a
real graph offline today (`ready`) or is a scaffold awaiting its fetched data. This is how
the product shows it isn't a single-organism app: the flagship AMR domain is one entry in
a registry, not the whole thing.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.ingestion.domains import DEFAULT_DOMAIN, list_domains

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("")
async def domains() -> dict:
    """List configured domains + readiness (no DB, deterministic)."""
    items = list_domains()
    return {
        "default": DEFAULT_DOMAIN,
        "domains": items,
        "counts": {
            "registered": len(items),
            "ready": sum(1 for d in items if d["ready"]),
        },
    }
