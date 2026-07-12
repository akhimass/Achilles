"""Grounding agent: turn extracted claims into evidence edges — but only if they
survive validation against reference-database facts.

This is the credibility gate. A claim from an abstract carries the paper's PMID as
provenance; if a reference DB (CARD/UniProt/ChEMBL) also corroborates it, we attach
that accession too and mark the edge grounded=True. Unsupported claims are dropped,
not stored. No edge is ever written without provenance.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import structured
from app.ai.extraction import ExtractedClaim
from app.config import settings
from app.models.domain import EvidenceEdge, NodeType, Relation
from app.sources import card, uniprot


class GroundingVerdict(BaseModel):
    supported: bool
    provenance_db: str | None = None
    provenance_acc: str | None = None
    adjusted_confidence: float = Field(ge=0, le=1)
    reason: str


# ─── Deterministic edge decision (the credibility gate, unit-tested) ──────────

_RELATIONS = {r.value: r for r in Relation}
_OBJECT_KINDS = {
    "drug": NodeType.drug,
    "target": NodeType.target,
    "gene": NodeType.gene,
    "mechanism": NodeType.mechanism,
}
# Claims weaker than this and unsupported by any reference are dropped, not stored.
DROP_FLOOR = 0.2


def decide_edge(
    claim: ExtractedClaim,
    verdict: GroundingVerdict | None,
    *,
    gene_id: UUID,
    gene_symbol: str | None,
    gene_locus: str | None,
    paper_pmid: str | None,
    extracted_by: str,
) -> EvidenceEdge | None:
    """Turn a claim + grounding verdict into an EvidenceEdge, or drop it.

    Three tiers (deterministic — no LLM here):
      - reference-supported  → grounded=True, PMID + CARD/UniProt accession, high confidence
      - abstract-only        → grounded=False, PMID only, confidence < 0.5 (visibly weaker)
      - too weak / malformed → dropped (None)
    Never returns an edge without a PMID; the EvidenceEdge validator also enforces
    that at least one provenance is present.
    """
    if not paper_pmid:
        return None
    relation = _RELATIONS.get((claim.relation or "").strip())
    if relation is None:
        return None
    obj = (claim.object or "").strip()
    if not obj:
        return None
    target_type = _OBJECT_KINDS.get((claim.object_kind or "").strip().lower(), NodeType.mechanism)

    supported = bool(verdict and verdict.supported and verdict.provenance_acc)
    if supported:
        grounded = True
        provenance_db = verdict.provenance_db
        provenance_acc = verdict.provenance_acc
        confidence = round(min(1.0, 0.5 + 0.5 * float(verdict.adjusted_confidence)), 3)
    else:
        if float(claim.confidence) < DROP_FLOOR:
            return None
        grounded = False
        provenance_db = None
        provenance_acc = None
        confidence = round(min(0.49, float(claim.confidence) * 0.6), 3)

    return EvidenceEdge(
        source_type=NodeType.gene,
        source_id=gene_id,
        relation=relation,
        target_type=target_type,
        target_literal=obj,
        provenance_pmid=paper_pmid,
        provenance_db=provenance_db,
        provenance_acc=provenance_acc,
        confidence=confidence,
        grounded=grounded,
        extracted_by=extracted_by,
        metadata={
            "subject": claim.subject,
            "object_kind": claim.object_kind,
            "evidence_span": claim.evidence_span,
            "gene_symbol": gene_symbol,
            "gene_locus": gene_locus,
            "verdict_reason": verdict.reason if verdict else None,
        },
    )


async def ground_claim(
    claim: ExtractedClaim, organism: str, *, gene_term: str | None = None
) -> GroundingVerdict:
    """Validate a single claim against reference facts pulled for its entities.

    `gene_term` overrides which gene/family symbol is looked up in CARD/UniProt
    (e.g. the MarR family) — homology-based grounding, how AMR annotation works —
    while the claim's specific extracted subject is preserved elsewhere. Defaults to
    the claim's subject.
    """
    facts = await _gather_reference_facts(claim, organism, gene_term=gene_term)
    return await structured(
        schema=GroundingVerdict,
        system=prompts.GROUND_SYSTEM,
        user=prompts.GROUND_USER.format(
            subject=gene_term or claim.subject,
            relation=claim.relation,
            object=claim.object,
            reference_facts=facts or "(none found)",
        ),
        model=settings.model_extract,
    )


async def _gather_reference_facts(
    claim: ExtractedClaim, organism: str, *, gene_term: str | None = None
) -> str:
    """Collect corroborating facts for the claim's entities from CARD/ARO + UniProt.

    Returns a compact, quotable fact block with accessions (ARO:xxxx, UniProt acc)
    that becomes edge provenance when the grounding verdict is supported.
    """
    term = gene_term or claim.subject
    card_facts = await card.lookup(term, claim.object, organism)
    uniprot_facts = await uniprot.lookup(term, organism)
    blocks = [b for b in (card_facts, uniprot_facts) if b]
    return "\n".join(blocks)
