"""Seed the evidence graph from the committed literature corpus (offline).

Reads data/demo/literature/corpus.json — public PubMed abstracts + grounded/ungrounded
edges produced once by `sources/make_literature_snapshot.py` — and upserts `papers`
and `evidence_edges`. No network, no LLM here: the LLM extraction/grounding already
ran in the snapshot builder and was committed, so `make seed` reproduces the exact
evidence graph offline.

Called by ingestion/seed.py after the strain/gene seed (edges reference genes).
Idempotent via stable UUIDs + upserts.

NOTE (embeddings): papers.embedding is left NULL — no public/deterministic embedding
model is wired here. Phase 3 (pgvector retrieval) should populate it via a configured
embedding provider; we never fabricate vectors.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from app.ingestion.seed import _burk_gene_id
from app.models.domain import EvidenceEdge

SNAPSHOT_LIT = Path(__file__).resolve().parents[3] / "data" / "demo" / "literature" / "corpus.json"


def _edge_id(edge: EvidenceEdge) -> UUID:
    key = "/".join(
        [
            str(edge.source_id),
            (edge.metadata or {}).get("subject") or "",
            edge.relation.value,
            edge.target_literal or str(edge.target_id),
            edge.provenance_pmid or "",
            edge.provenance_acc or "",
        ]
    )
    return uuid5(NAMESPACE_URL, f"achilles/edge/{key}")


def load_corpus() -> dict:
    if not SNAPSHOT_LIT.exists():
        raise FileNotFoundError(
            f"literature corpus missing: {SNAPSHOT_LIT}\n"
            "Build it with:  cd backend && python -m app.sources.make_literature_snapshot"
        )
    return json.loads(SNAPSHOT_LIT.read_text())


def rebuild_edges(corpus: dict) -> list[EvidenceEdge]:
    """Reconstruct validated EvidenceEdges from the committed corpus (pure).

    source_id is recomputed from the public gene locus so edges bind to the seeded
    gene regardless of any id-scheme drift. Rows that fail the EvidenceEdge validator
    (provenance/target invariants) are dropped, never bypassed.
    """
    edges: list[EvidenceEdge] = []
    for raw in corpus.get("edges", []):
        locus = raw.get("gene_locus") or (raw.get("metadata") or {}).get("gene_locus")
        if not locus:
            continue
        payload = {k: v for k, v in raw.items() if k not in ("gene_locus", "paper_title", "paper_year")}
        payload["source_id"] = str(_burk_gene_id(locus))
        try:
            edges.append(EvidenceEdge.model_validate(payload))
        except Exception:
            continue
    return edges


async def upsert_papers_and_edges(papers: list[dict], edges: list[EvidenceEdge]) -> dict:
    """Upsert papers then evidence_edges (FK-safe order). Idempotent. Returns a summary.

    Shared by the offline seed and the live `/api/literature/ingest` path.
    """
    from sqlalchemy import text

    from app.db import SessionLocal

    async with SessionLocal() as session:
        async with session.begin():
            if papers:
                await session.execute(
                    text(
                        """
                        INSERT INTO papers (id, pmid, doi, title, abstract, year, source, metadata)
                        VALUES (:id, :pmid, :doi, :title, :abstract, :year, :source, CAST(:metadata AS jsonb))
                        ON CONFLICT (pmid) DO UPDATE
                          SET title = EXCLUDED.title, abstract = EXCLUDED.abstract,
                              doi = EXCLUDED.doi, year = EXCLUDED.year, metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "id": str(uuid5(NAMESPACE_URL, f"achilles/paper/{p['pmid']}")),
                            "pmid": p["pmid"],
                            "doi": p.get("doi"),
                            "title": p["title"],
                            "abstract": p.get("abstract"),
                            "year": p.get("year"),
                            "source": p.get("source", "europepmc"),
                            "metadata": json.dumps(p.get("metadata", {})),
                        }
                        for p in papers
                        if p.get("pmid")
                    ],
                )

            # Only write edges whose paper is present (FK: provenance_pmid -> papers).
            known_pmids = {p["pmid"] for p in papers if p.get("pmid")}
            rows = [
                {
                    "id": str(_edge_id(e)),
                    "source_type": e.source_type.value,
                    "source_id": str(e.source_id),
                    "relation": e.relation.value,
                    "target_type": e.target_type.value,
                    "target_id": str(e.target_id) if e.target_id else None,
                    "target_literal": e.target_literal,
                    "provenance_pmid": e.provenance_pmid,
                    "provenance_db": e.provenance_db,
                    "provenance_acc": e.provenance_acc,
                    "confidence": e.confidence,
                    "extracted_by": e.extracted_by,
                    "grounded": e.grounded,
                    "metadata": json.dumps(e.metadata),
                }
                for e in edges
                if e.provenance_pmid in known_pmids
            ]
            if rows:
                await session.execute(
                    text(
                        """
                        INSERT INTO evidence_edges
                          (id, source_type, source_id, relation, target_type, target_id,
                           target_literal, provenance_pmid, provenance_db, provenance_acc,
                           confidence, extracted_by, grounded, metadata)
                        VALUES
                          (:id, :source_type, :source_id, :relation, :target_type, :target_id,
                           :target_literal, :provenance_pmid, :provenance_db, :provenance_acc,
                           :confidence, :extracted_by, :grounded, CAST(:metadata AS jsonb))
                        ON CONFLICT (id) DO UPDATE
                          SET confidence = EXCLUDED.confidence, grounded = EXCLUDED.grounded,
                              provenance_db = EXCLUDED.provenance_db,
                              provenance_acc = EXCLUDED.provenance_acc,
                              metadata = EXCLUDED.metadata
                        """
                    ),
                    rows,
                )

    grounded = sum(1 for e in edges if e.grounded)
    return {
        "papers": len(papers),
        "edges": len(edges),
        "grounded": grounded,
        "pct_grounded": round(100 * grounded / len(edges), 1) if edges else 0.0,
    }


async def seed_literature() -> dict:
    """Read the committed corpus and upsert it (offline). Returns a summary."""
    corpus = load_corpus()
    summary = await upsert_papers_and_edges(corpus.get("papers", []), rebuild_edges(corpus))
    print(
        f"seed(literature): {summary['papers']} papers, {summary['edges']} evidence edges "
        f"({summary['pct_grounded']}% grounded, embeddings NULL — see TODO)"
    )
    return summary
