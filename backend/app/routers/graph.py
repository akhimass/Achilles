"""Graph endpoints: the lineage tree and the evidence subgraph the frontend renders."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.graph_shaping import shape_evidence, shape_lineage

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/lineage")
async def lineage(organism: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Return the strain lineage tree for an organism (nodes + parent edges).

    Each node carries `flipper_count` (variants flagged is_flipper on that strain)
    for the gradient coloring, plus ST / year / country for the hover card.
    """
    result = await session.execute(
        text(
            """
            SELECT s.id,
                   s.label,
                   s.parent_id,
                   s.metadata->>'st'            AS st,
                   s.metadata->>'year'          AS year,
                   s.metadata->>'country'       AS country,
                   s.metadata->>'lineage_label' AS lineage,
                   (s.metadata->>'founder')::boolean AS founder,
                   COALESCE(f.cnt, 0)           AS flipper_count
            FROM strains s
            LEFT JOIN (
                SELECT strain_id, COUNT(*) AS cnt
                FROM variants
                WHERE is_flipper
                GROUP BY strain_id
            ) f ON f.strain_id = s.id
            WHERE s.organism = :organism
            ORDER BY s.label
            """
        ),
        {"organism": organism},
    )
    rows = [dict(r) for r in result.mappings().all()]
    return shape_lineage(rows)


@router.get("/strain")
async def strain(id: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Return one strain plus its flipper genes (for the detail rail + structure view)."""
    srow = (
        await session.execute(
            text("SELECT id, external_id, label, source, metadata FROM strains WHERE id = :id"),
            {"id": id},
        )
    ).mappings().first()
    if srow is None:
        return {"strain": None, "genes": []}

    grows = (
        await session.execute(
            text(
                """
                SELECT v.metadata->>'locus_tag'   AS locus_tag,
                       v.metadata->>'gene_symbol' AS gene_symbol,
                       v.metadata->>'product'     AS product,
                       v.metadata->>'chrom'       AS chrom,
                       (v.metadata->>'indel_delta')::int    AS indel_delta,
                       (v.metadata->>'flipper_support')::int AS flipper_support,
                       v.is_flipper                AS is_flipper,
                       v.effect                    AS effect,
                       g.metadata->>'wp'           AS wp
                FROM variants v
                JOIN genes g ON g.id = v.gene_id
                WHERE v.strain_id = :id
                ORDER BY v.is_flipper DESC,
                         (v.metadata->>'flipper_support')::int DESC NULLS LAST,
                         v.metadata->>'locus_tag'
                """
            ),
            {"id": id},
        )
    ).mappings().all()

    return {
        "strain": {
            "id": str(srow["id"]),
            "external_id": srow["external_id"],
            "label": srow["label"],
            "source": srow["source"],
            "metadata": srow["metadata"],
        },
        "genes": [dict(g) for g in grows],
    }


@router.get("/evidence")
async def evidence(
    node_type: str = "gene",
    node_id: str = "",
    organism: str = "Burkholderia multivorans",
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return the grounded evidence subgraph for a gene (for the EvidencePanel).

    `node_id` may be a gene UUID or a locus tag (what the UI has). Each edge carries
    relation, target, confidence, grounded flag, and resolved provenance links.
    """
    # Resolve the gene: try UUID, else locus tag.
    grow = (
        await session.execute(
            text(
                """
                SELECT id, locus_tag, name, product FROM genes
                WHERE organism = :organism
                  AND (locus_tag = :node_id OR CAST(id AS text) = :node_id)
                LIMIT 1
                """
            ),
            {"organism": organism, "node_id": node_id},
        )
    ).mappings().first()

    gene = {
        "id": str(grow["id"]) if grow else None,
        "locus_tag": grow["locus_tag"] if grow else node_id,
        "symbol": (grow["name"] if grow else None),
        "product": (grow["product"] if grow else None),
    }
    if grow is None or node_type != "gene":
        return shape_evidence(gene, [])

    rows = (
        await session.execute(
            text(
                """
                SELECT e.id, e.relation, e.target_type, e.target_id, e.target_literal,
                       e.confidence, e.grounded, e.provenance_pmid, e.provenance_db,
                       e.provenance_acc, e.extracted_by, e.metadata,
                       p.title AS paper_title, p.year AS paper_year
                FROM evidence_edges e
                LEFT JOIN papers p ON p.pmid = e.provenance_pmid
                WHERE e.source_type = 'gene' AND e.source_id = :gid
                """
            ),
            {"gid": grow["id"]},
        )
    ).mappings().all()

    return shape_evidence(gene, [dict(r) for r in rows])
