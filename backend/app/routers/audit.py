"""Audit endpoint — a tamper-evident, re-verifiable receipt for the prove-it result.

`GET /api/audit` runs the self-validation and returns a hash-CHAINED ledger of every
control adjudication plus a single head fingerprint. `POST /api/audit/verify` re-walks a
submitted ledger and recomputes its hashes, so a downloaded report (or one edited in the
browser) can be checked independently — change one verdict and the chain no longer
validates. The verdicts themselves are deterministic, so the fingerprint is stable.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import build_ledger, chain_head, observations_from_validation, verify_ledger
from app.db import get_session
from app.ingestion.domains import DEFAULT_ORGANISM
from app.ingestion.validation import evaluate, load_benchmark
from app.routers.validation import _fetch_edges

router = APIRouter(prefix="/api/audit", tags=["audit"])

_DEFAULT_ORGANISM = DEFAULT_ORGANISM


@router.get("")
async def audit(
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Build a hash-chained ledger over the live self-validation result."""
    edges = await _fetch_edges(session, organism)
    benchmark = load_benchmark()
    if organism:
        benchmark = {**benchmark, "organism": organism}
    report = evaluate(benchmark, edges).model_dump()

    ledger = build_ledger(observations_from_validation(report))
    return {
        "organism": organism,
        "algorithm": "sha256, hash-chained (each entry folds in the previous)",
        "metrics": report["metrics"],
        "entries": len(ledger),
        "head": chain_head(ledger),
        "ledger": ledger,
    }


@router.post("/verify")
async def verify(payload: dict = Body(...)) -> dict:
    """Re-walk a submitted ledger and confirm its hash chain. Detects any tamper."""
    ledger = payload.get("ledger") or []
    return verify_ledger(ledger)
