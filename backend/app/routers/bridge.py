"""Bridge endpoint — one grounded finding, translated researcher → physician.

`GET /api/bridge?gene=<name|locus>` composes a single gene's GROUNDED evidence into two
lenses: the researcher's target-identification view (mechanism, ranked target, structure)
and the physician's treatment view (drugs it drives resistance to, the cited
collateral-sensitivity opening, a cycling hypothesis) — carrying the same provenance
across the handoff. Deterministic composition of already-grounded data; nothing generated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bridge_shaping import shape_bridge
from app.db import get_session
from app.graph_shaping import pubmed_url, reference_url
from app.ingestion.validation import resolve_locus
from app.routers.treatment import CollateralPair, _CS_SQL, propose_cycle, shape_cycle

router = APIRouter(prefix="/api/bridge", tags=["bridge"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_GENE_SQL = """
    SELECT locus_tag, name, product, metadata->>'wp' AS wp
    FROM genes WHERE locus_tag = :locus AND organism = :organism
"""
_EDGES_SQL = """
    SELECT e.relation, e.target_literal AS target,
           e.provenance_pmid, e.provenance_db, e.provenance_acc
    FROM evidence_edges e
    JOIN genes g ON g.id = e.source_id
    WHERE e.source_type = 'gene' AND g.locus_tag = :locus
      AND g.organism = :organism AND e.grounded = TRUE
"""
_TARGET_SQL = """
    SELECT t.rank_score, t.tractability, t.pdb_ids
    FROM targets t
    JOIN genes g ON g.id = t.gene_id
    WHERE g.locus_tag = :locus AND g.organism = :organism
    LIMIT 1
"""


@router.get("")
async def bridge(
    gene: str,
    organism: str = _DEFAULT_ORGANISM,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Translate one gene's grounded finding from bench to bedside."""
    locus = resolve_locus(gene) or gene
    params = {"locus": locus, "organism": organism}

    grow = (await session.execute(text(_GENE_SQL), params)).mappings().first()
    if grow is None:
        return {"gene": {"locus": locus}, "found": False,
                "reason": f"'{gene}' is not a gene in this dataset."}

    gene_row = {"locus": grow["locus"], "name": grow["name"], "product": grow["product"]}

    edges = [
        {
            "relation": r["relation"],
            "target": r["target"],
            "provenance": {
                "pmid": r["provenance_pmid"], "pubmed_url": pubmed_url(r["provenance_pmid"]),
                "db": r["provenance_db"], "acc": r["provenance_acc"],
                "ref_url": reference_url(r["provenance_db"], r["provenance_acc"]),
            },
        }
        for r in (await session.execute(text(_EDGES_SQL), params)).mappings().all()
    ]

    trow = (await session.execute(text(_TARGET_SQL), params)).mappings().first()
    target = None
    if trow is not None:
        tract = trow["tractability"] or {}
        target = {
            "rank_score": trow["rank_score"],
            "tractability_bucket": tract.get("bucket") if isinstance(tract, dict) else None,
            "structure_available": bool(grow["wp"] or (trow["pdb_ids"] or [])),
        }

    # Cited collateral-sensitivity cycle for the organism (the clinic-side strategy).
    cs_rows = (await session.execute(text(_CS_SQL), {"organism": organism})).mappings().all()
    pairs = [
        CollateralPair(
            organism=r["organism"], drug_a=r["drug_a"], drug_b=r["drug_b"],
            reciprocal=bool(r["reciprocal"]), strength=r["strength"],
            n_lineages=r["n_lineages"], metadata=r["metadata"] or {},
        )
        for r in cs_rows
    ]
    cycle = shape_cycle(organism, propose_cycle(pairs), pairs) if pairs else None

    out = shape_bridge(gene_row, edges, target=target, cycle=cycle, organism=organism)
    out["found"] = True
    return out
