"""Domain models — the contract between ingestion, the AI layer, the API, and the
frontend. `frontend/src/lib/types.ts` mirrors these shapes; keep them in sync.

Rule of the road: extend these (add optional fields) — never break an existing
shape. Everything downstream assumes these fields exist and mean what they say.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ─── Enums ───────────────────────────────────────────────────────────────────


class VariantKind(str, Enum):
    snp = "snp"
    indel = "indel"


class VariantEffect(str, Enum):
    synonymous = "synonymous"
    nonsynonymous = "nonsynonymous"
    frameshift = "frameshift"
    intergenic = "intergenic"


class NodeType(str, Enum):
    strain = "strain"
    variant = "variant"
    gene = "gene"
    target = "target"
    drug = "drug"
    mechanism = "mechanism"


class Relation(str, Enum):
    confers_resistance = "confers_resistance"
    sensitizes_to = "sensitizes_to"
    is_target_of = "is_target_of"
    implicates = "implicates"
    reverts_with = "reverts_with"


# ─── Nodes ───────────────────────────────────────────────────────────────────


class Strain(BaseModel):
    id: UUID | None = None
    external_id: str
    source: str  # 'bvbrc' | 'ncbi_pathogen' | 'user'
    organism: str
    label: str | None = None
    parent_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class Gene(BaseModel):
    id: UUID | None = None
    locus_tag: str
    name: str | None = None
    product: str | None = None
    uniprot_acc: str | None = None
    organism: str
    metadata: dict = Field(default_factory=dict)


class Variant(BaseModel):
    id: UUID | None = None
    strain_id: UUID
    kind: VariantKind
    ref_position: int
    ref_allele: str | None = None
    alt_allele: str | None = None
    gene_id: UUID | None = None
    effect: VariantEffect | None = None
    allele_freq: float | None = Field(default=None, ge=0, le=1)
    is_flipper: bool = False
    metadata: dict = Field(default_factory=dict)


class Target(BaseModel):
    id: UUID | None = None
    gene_id: UUID
    mechanism: str | None = None
    tractability: dict = Field(default_factory=dict)
    pdb_ids: list[str] = Field(default_factory=list)
    rank_score: float | None = Field(default=None, ge=0, le=1)
    metadata: dict = Field(default_factory=dict)


class Paper(BaseModel):
    id: UUID | None = None
    pmid: str | None = None
    doi: str | None = None
    title: str
    abstract: str | None = None
    year: int | None = None
    source: str = "europepmc"
    metadata: dict = Field(default_factory=dict)


# ─── The edge: the core object ───────────────────────────────────────────────


class EvidenceEdge(BaseModel):
    """A single grounded relationship. Provenance is never fully null — exactly one
    of `provenance_pmid` or `provenance_acc` must be present. This invariant is the
    whole point of the product and is enforced both here and by a DB CHECK.
    """

    id: UUID | None = None
    source_type: NodeType
    source_id: UUID
    relation: Relation
    target_type: NodeType
    target_id: UUID | None = None
    target_literal: str | None = None  # e.g. a drug name when target_id is absent

    provenance_pmid: str | None = None
    provenance_db: str | None = None  # 'CARD' | 'UniProt' | 'ChEMBL'
    provenance_acc: str | None = None

    confidence: float = Field(ge=0, le=1)
    extracted_by: str | None = None
    grounded: bool = False
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None

    @model_validator(mode="after")
    def _require_provenance(self) -> "EvidenceEdge":
        if self.provenance_pmid is None and self.provenance_acc is None:
            raise ValueError(
                "EvidenceEdge requires provenance: set provenance_pmid or provenance_acc"
            )
        if self.target_id is None and self.target_literal is None:
            raise ValueError("EvidenceEdge requires target_id or target_literal")
        return self


# ─── Collateral sensitivity (deterministic) ──────────────────────────────────


class CollateralPair(BaseModel):
    """Resistance to `drug_a` induces sensitivity to `drug_b`. Computed, never
    inferred by an LLM. `reciprocal` marks an RCS pair — the basis for cycling."""

    id: UUID | None = None
    organism: str
    drug_a: str
    drug_b: str
    reciprocal: bool = False
    strength: float | None = None
    n_lineages: int | None = None
    metadata: dict = Field(default_factory=dict)


# ─── Trajectory retrieval (deterministic; the counterfactual beat) ────────────


class ObservedNext(BaseModel):
    """One drug that became sensitive again ('viable') in real lineages after a
    resistance event. Purely observed — retrieved from the data, never predicted."""

    sensitized_to: str
    n_lineages: int
    n_strains: int
    backing_strains: list[str] = Field(default_factory=list)  # real strain external ids
    lineages: list[str] = Field(default_factory=list)


class TrajectoryEvidence(BaseModel):
    """What real evolved lineages DID after acquiring resistance to `resisted`.

    This is RETRIEVAL over real observed transitions, never generation. Every entry
    traces to specific real strains/lineages. `kind` is always ``"retrieved"``; if the
    data can't support an answer, ``sufficient`` is False and `note` says so — a gap is
    shown honestly, never filled with a fabricated trajectory.
    """

    organism: str
    resisted: str
    event_strain: str | None = None  # external id of the anchoring strain, if any
    observed_next: list[ObservedNext] = Field(default_factory=list)
    support_lineages: int = 0
    backing_strains: list[str] = Field(default_factory=list)
    sufficient: bool = False
    kind: str = "retrieved"  # NEVER 'predicted' / 'generated' / 'simulated'
    note: str | None = None
    provenance: dict = Field(default_factory=dict)
