"""Target endpoints: ranked candidate targets with evidence, tractability, rationale.

The rank_score is computed deterministically upstream (ingestion/scoring.py) and only
read here. Each target carries its grounded evidence edges, ChEMBL tractability, and a
citation-backed rationale. The rationale is deterministic by default (offline-
reproducible); pass `narrate=true` to enrich it with an `ai/targets.py` LLM narration,
which may reword the rationale but must never change the score.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.targets_shaping import apply_cached_rationales, shape_targets

router = APIRouter(prefix="/api/targets", tags=["targets"])

_DEFAULT_ORGANISM = "Burkholderia multivorans"

_TARGETS_SQL = """
    SELECT t.id, t.gene_id, t.mechanism, t.tractability, t.pdb_ids, t.rank_score,
           t.metadata,
           g.locus_tag, g.name, g.product, g.metadata->>'wp' AS wp
    FROM targets t
    JOIN genes g ON g.id = t.gene_id
    WHERE g.organism = :organism
    ORDER BY t.rank_score DESC NULLS LAST, g.locus_tag
"""

_EDGES_SQL = """
    SELECT e.source_id, e.relation, e.target_type, e.target_id, e.target_literal,
           e.confidence, e.grounded, e.provenance_pmid, e.provenance_db,
           e.provenance_acc, e.extracted_by, e.metadata,
           p.title AS paper_title, p.year AS paper_year
    FROM evidence_edges e
    LEFT JOIN papers p ON p.pmid = e.provenance_pmid
    WHERE e.source_type = 'gene' AND CAST(e.source_id AS text) = ANY(:gene_ids)
"""

_STRAIN_FLAGS_SQL = """
    SELECT gene_id,
           BOOL_OR(TRUE)       AS in_strain,
           BOOL_OR(is_flipper) AS strain_flipper
    FROM variants
    WHERE CAST(strain_id AS text) = :strain_id AND CAST(gene_id AS text) = ANY(:gene_ids)
    GROUP BY gene_id
"""


@router.get("")
async def list_targets(
    strain_id: str | None = None,
    organism: str | None = None,
    narrate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Ranked candidate targets for a strain (or the organism), with evidence + rationale.

    `strain_id` scopes the organism and annotates each target with whether the strain
    carries a (flipper) variant in that gene. Targets themselves are organism-level
    (a gene promoted to "worth acting on"); the full ranked list is always returned so
    the panel never dead-ends when a strain carries only a few of them.
    """
    strain_view: dict | None = None
    resolved_org = organism or _DEFAULT_ORGANISM

    if strain_id:
        srow = (
            await session.execute(
                text("SELECT id, label, organism FROM strains WHERE id = :id"),
                {"id": strain_id},
            )
        ).mappings().first()
        if srow is not None:
            strain_view = {"id": str(srow["id"]), "label": srow["label"]}
            resolved_org = srow["organism"]

    target_rows = [
        dict(r)
        for r in (
            await session.execute(text(_TARGETS_SQL), {"organism": resolved_org})
        ).mappings().all()
    ]
    if not target_rows:
        return shape_targets(strain_view, resolved_org, [], {}, {})

    gene_ids = [str(r["gene_id"]) for r in target_rows]

    edge_rows = (
        await session.execute(text(_EDGES_SQL), {"gene_ids": gene_ids})
    ).mappings().all()
    edges_by_gene: dict[str, list[dict]] = {}
    for r in edge_rows:
        edges_by_gene.setdefault(str(r["source_id"]), []).append(dict(r))

    strain_flags: dict[str, dict] = {}
    if strain_id and strain_view is not None:
        frows = (
            await session.execute(
                text(_STRAIN_FLAGS_SQL), {"strain_id": strain_id, "gene_ids": gene_ids}
            )
        ).mappings().all()
        strain_flags = {
            str(r["gene_id"]): {"in_strain": bool(r["in_strain"]), "strain_flipper": bool(r["strain_flipper"])}
            for r in frows
        }

    payload = shape_targets(strain_view, resolved_org, target_rows, edges_by_gene, strain_flags)

    if narrate:
        # Opt-in live override: call the model now (best-effort, never blocks/raises).
        await _enrich_with_narration(payload)
    else:
        # Default: serve pre-reviewed, committed narration (cached) when available;
        # otherwise the deterministic rationale already set by shaping. No live call.
        from app.ai.narration_cache import load_target_rationales

        apply_cached_rationales(payload, load_target_rationales())

    return payload


async def _enrich_with_narration(payload: dict) -> None:
    """Best-effort LLM narration for the top targets; deterministic rationale on failure.

    Never raises into the request and never touches rank_score. If no API key / network
    is available, targets keep their deterministic rationale (rationale_source stays
    'deterministic').
    """
    from app.ai.targets import narrate_target

    for t in payload.get("targets", [])[:3]:  # top few only, to bound latency/cost
        try:
            edges_txt = "\n".join(
                f"- {e['relation']} {e.get('target')} (conf {e['confidence']:.2f}, "
                f"{'grounded' if e['grounded'] else 'ungrounded'}; "
                f"{e['provenance'].get('db') or 'PMID'}:{e['provenance'].get('acc') or e['provenance'].get('pmid')})"
                for e in t.get("evidence", [])
            )
            tract = t.get("tractability") or {}
            tract_txt = (
                "no known ChEMBL chemical matter (novel)"
                if tract.get("assessed") and not tract.get("has_target")
                else str(tract)
            )
            result = await narrate_target(
                gene=t.get("name") or t.get("locus_tag") or "gene",
                product=t.get("product") or "",
                rank_score=t.get("rank_score") or 0.0,
                edges=edges_txt or "(none)",
                tractability=tract_txt,
            )
            if result and result.narrative:
                t["rationale"] = result.narrative
                if result.citations:
                    t["rationale_citations"] = result.citations
                t["rationale_source"] = "llm"
        except Exception:
            continue  # keep deterministic rationale
