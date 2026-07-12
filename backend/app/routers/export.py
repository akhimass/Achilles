"""Reproducibility export: download the evidence graph for a selection as receipts.

`GET /api/export/evidence?gene=<locus>&format=json|csv` returns a citable artifact for
one gene's evidence subgraph — every edge, its confidence, and all provenance ids
(PMIDs + reference accessions) — under a methods header naming the deterministic
pipeline and public sources. Public data only; deterministic shaping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.export_shaping import build_evidence_export, evidence_export_csv
from app.graph_shaping import shape_evidence

router = APIRouter(prefix="/api/export", tags=["export"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_GENE_SQL = """
    SELECT id, locus_tag, name, product FROM genes
    WHERE organism = :organism AND (locus_tag = :gene OR CAST(id AS text) = :gene)
    LIMIT 1
"""

_EDGES_SQL = """
    SELECT e.id, e.relation, e.target_type, e.target_id, e.target_literal,
           e.confidence, e.grounded, e.provenance_pmid, e.provenance_db,
           e.provenance_acc, e.extracted_by, e.metadata,
           p.title AS paper_title, p.year AS paper_year
    FROM evidence_edges e
    LEFT JOIN papers p ON p.pmid = e.provenance_pmid
    WHERE e.source_type = 'gene' AND e.source_id = :gid
"""


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (s or "gene")).strip("-") or "gene"


@router.get("/evidence")
async def export_evidence(
    gene: str,
    organism: str = _DEFAULT_ORGANISM,
    format: str = "json",
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Export a gene's grounded evidence subgraph as a citable JSON or CSV artifact."""
    grow = (
        await session.execute(text(_GENE_SQL), {"organism": organism, "gene": gene})
    ).mappings().first()

    gene_view = {
        "id": str(grow["id"]) if grow else None,
        "locus_tag": grow["locus_tag"] if grow else gene,
        "symbol": grow["name"] if grow else None,
        "product": grow["product"] if grow else None,
    }

    rows: list[dict] = []
    if grow is not None:
        rows = [
            dict(r)
            for r in (
                await session.execute(text(_EDGES_SQL), {"gid": grow["id"]})
            ).mappings().all()
        ]

    shaped = shape_evidence(gene_view, rows)  # deterministic edge shaping (with trace)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    export = build_evidence_export(gene_view, shaped["edges"], organism, generated_at)

    stem = f"achilles-evidence-{_slug(gene_view['locus_tag'])}"
    if format.lower() == "csv":
        body = evidence_export_csv(export)
        return Response(
            content=body,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{stem}.csv"'},
        )
    return Response(
        content=json.dumps(export, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
    )
