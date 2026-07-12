"""Promote evidence-supported genes into ranked `targets` (Phase 3).

Runs after the strain/gene seed and the literature seed, because it reads the
evidence edges that literature grounding produced. For every gene that carries at
least one evidence edge, it:

  1. Summarizes that gene's edges (count, mean confidence, grounded count) and reads
     its flipper support — all already computed deterministically upstream.
  2. Computes a 0–1 `rank_score` with `ingestion/scoring.py` (pure, LLM-free).
  3. Attaches ChEMBL tractability from the committed cache (network-free here).
  4. Upserts a row into `targets` with a stable id.

No LLM, no network in this module (ChEMBL is read from the committed cache). The
narration in `ai/targets.py` is layered on at request time and never changes the
score. Idempotent via a stable uuid5 target id.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.ingestion.scoring import GeneEvidenceStats, score_gene
from app.models.domain import Target
from app.sources import chembl

ORGANISM = "Burkholderia multivorans"

# Public, auditable locus → UniProt accession map (from the committed UniProt cache
# under data/demo/reference/). Used only to look up ChEMBL tractability by accession.
TARGET_UNIPROT: dict[str, str] = {
    "A8H40_RS07590": "A0A0H3KEU2",  # MarR family regulator
    "A8H40_RS24275": "A0ABU2DWC3",  # AraC/MarA-family activator
    "A8H40_RS17945": "Q84BW1",      # LysR family regulator
    "A8H40_RS19975": "A0A0H3KEK0",  # DMT-family efflux transporter
    "A8H40_RS00780": "A0A0H3KHN7",  # two-component response regulator
}

# Human mechanism label per candidate locus (falls back to the gene product).
TARGET_MECHANISM: dict[str, str] = {
    "A8H40_RS07590": "Efflux regulation — MarR repressor of the marRAB operon",
    "A8H40_RS24275": "Efflux activation — AraC/MarA-family transcriptional activator",
    "A8H40_RS17945": "Transcriptional regulation — LysR family",
    "A8H40_RS19975": "Drug efflux — DMT-family transporter",
    "A8H40_RS00780": "Two-component signaling — response regulator",
}


def _target_id(gene_id: str | UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/target/{gene_id}")


def build_target(row: dict) -> Target:
    """Build one ranked Target from a gene's edge-stat row (pure, testable).

    `row` carries: gene_id, locus_tag, name, product, flipper_support, n_edges,
    mean_confidence, grounded_edges, wp. Tractability is read from the ChEMBL cache
    (network-free). The rank_score comes from `scoring.py` and is never altered here.
    """
    locus = row["locus_tag"]
    stats = GeneEvidenceStats(
        gene_id=str(row["gene_id"]),
        locus_tag=locus,
        n_edges=int(row.get("n_edges") or 0),
        mean_confidence=float(row.get("mean_confidence") or 0.0),
        grounded_edges=int(row.get("grounded_edges") or 0),
        flipper_support=int(row.get("flipper_support") or 0),
    )
    scored = score_gene(stats)

    acc = TARGET_UNIPROT.get(locus)
    tractability = chembl.tractability_from_cache(acc)
    if acc and not tractability.get("queried_acc"):
        tractability["queried_acc"] = acc

    mechanism = TARGET_MECHANISM.get(locus) or row.get("product")
    return Target(
        id=_target_id(row["gene_id"]),
        gene_id=row["gene_id"],
        mechanism=mechanism,
        tractability=tractability,
        pdb_ids=[],  # AlphaFold-predicted structures are reached via /api/structure by locus
        rank_score=scored.rank_score,
        metadata={
            "locus_tag": locus,
            "name": row.get("name"),
            "product": row.get("product"),
            "wp": row.get("wp"),
            "uniprot_acc": acc,
            "score_components": {
                "evidence": scored.evidence_component,
                "flipper": scored.flipper_component,
                "n_edges": scored.n_edges,
                "grounded_edges": scored.grounded_edges,
                "mean_confidence": scored.mean_confidence,
                "flipper_support": scored.flipper_support,
            },
        },
    )


def build_targets(rows: list[dict]) -> list[Target]:
    """Build and rank Targets from gene edge-stat rows (pure). Highest score first."""
    targets = [build_target(r) for r in rows]
    targets.sort(key=lambda t: (-(t.rank_score or 0.0), t.metadata.get("locus_tag") or ""))
    return targets


# ─── DB read + persist (the only I/O; still network-free) ────────────────────

_GENE_STATS_SQL = """
    SELECT g.id                                   AS gene_id,
           g.locus_tag                            AS locus_tag,
           g.name                                 AS name,
           g.product                              AS product,
           g.metadata->>'wp'                      AS wp,
           COALESCE((g.metadata->>'flipper_support')::int, 0) AS flipper_support,
           COUNT(e.id)                            AS n_edges,
           COALESCE(AVG(e.confidence), 0)         AS mean_confidence,
           COALESCE(SUM(CASE WHEN e.grounded THEN 1 ELSE 0 END), 0) AS grounded_edges
    FROM genes g
    JOIN evidence_edges e
      ON e.source_type = 'gene' AND e.source_id = g.id
    WHERE g.organism = :organism
    GROUP BY g.id, g.locus_tag, g.name, g.product, g.metadata
"""


async def seed_targets(organism: str = ORGANISM) -> dict:
    """Read evidence-supported genes, rank them, and upsert ranked targets."""
    import json

    from sqlalchemy import text

    from app.db import SessionLocal

    async with SessionLocal() as session:
        rows = (
            await session.execute(text(_GENE_STATS_SQL), {"organism": organism})
        ).mappings().all()
        targets = build_targets([dict(r) for r in rows])

        if targets:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO targets (id, gene_id, mechanism, tractability, pdb_ids,
                                             rank_score, metadata)
                        VALUES (:id, :gene_id, :mechanism, CAST(:tractability AS jsonb),
                                :pdb_ids, :rank_score, CAST(:metadata AS jsonb))
                        ON CONFLICT (id) DO UPDATE
                          SET mechanism = EXCLUDED.mechanism,
                              tractability = EXCLUDED.tractability,
                              pdb_ids = EXCLUDED.pdb_ids,
                              rank_score = EXCLUDED.rank_score,
                              metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "id": str(t.id),
                            "gene_id": str(t.gene_id),
                            "mechanism": t.mechanism,
                            "tractability": json.dumps(t.tractability),
                            "pdb_ids": t.pdb_ids,
                            "rank_score": t.rank_score,
                            "metadata": json.dumps(t.metadata),
                        }
                        for t in targets
                    ],
                )

    top = targets[0] if targets else None
    print(
        f"seed(targets): {len(targets)} ranked targets"
        + (f" — top {top.metadata.get('locus_tag')} rank_score={top.rank_score}" if top else "")
    )
    return {
        "targets": len(targets),
        "top_locus": top.metadata.get("locus_tag") if top else None,
        "top_score": top.rank_score if top else None,
    }
