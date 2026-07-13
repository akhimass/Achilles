"""Report endpoint — the auditable receipt as a downloadable file.

`GET /api/report/validation` returns a self-contained HTML audit report (the 29-control
self-validation + its hash-chained ledger + re-verify instructions) with a download
disposition, so a researcher can save or share a keepable, re-verifiable artifact.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import build_ledger, chain_head, observations_from_validation
from app.db import get_session
from app.ingestion.validation import evaluate, load_benchmark
from app.report import validation_report_html
from app.routers.validation import _fetch_edges

router = APIRouter(prefix="/api/report", tags=["report"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"


@router.get("/validation", response_class=HTMLResponse)
async def validation_report(
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> HTMLResponse:
    """A downloadable, self-contained, re-verifiable audit report (HTML)."""
    edges = await _fetch_edges(session, organism)
    benchmark = load_benchmark()
    if organism:
        benchmark = {**benchmark, "organism": organism}
    report = evaluate(benchmark, edges).model_dump()
    ledger = build_ledger(observations_from_validation(report))
    html_str = validation_report_html(report, ledger, chain_head(ledger), organism=organism)
    return HTMLResponse(
        content=html_str,
        headers={"Content-Disposition": 'attachment; filename="achilles-audit-report.html"'},
    )
