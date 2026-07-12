// Mirror of backend/app/models/domain.py. Keep in sync — when the Pydantic models
// gain a field, add it here too. These shapes are the contract the UI renders.

export type VariantKind = "snp" | "indel";
export type VariantEffect =
  | "synonymous"
  | "nonsynonymous"
  | "frameshift"
  | "intergenic";
export type NodeType =
  | "strain"
  | "variant"
  | "gene"
  | "target"
  | "drug"
  | "mechanism";
export type Relation =
  | "confers_resistance"
  | "sensitizes_to"
  | "is_target_of"
  | "implicates"
  | "reverts_with";

export interface Strain {
  id: string;
  external_id: string;
  source: string;
  organism: string;
  label?: string | null;
  parent_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface Variant {
  id: string;
  strain_id: string;
  kind: VariantKind;
  ref_position: number;
  ref_allele?: string | null;
  alt_allele?: string | null;
  gene_id?: string | null;
  effect?: VariantEffect | null;
  allele_freq?: number | null;
  is_flipper: boolean;
  metadata: Record<string, unknown>;
}

export interface Target {
  id: string;
  gene_id: string;
  mechanism?: string | null;
  tractability: Record<string, unknown>;
  pdb_ids: string[];
  rank_score?: number | null;
  metadata: Record<string, unknown>;
}

// The core object. Provenance is never fully null (enforced server-side).
export interface EvidenceEdge {
  id: string;
  source_type: NodeType;
  source_id: string;
  relation: Relation;
  target_type: NodeType;
  target_id?: string | null;
  target_literal?: string | null;
  provenance_pmid?: string | null;
  provenance_db?: string | null;
  provenance_acc?: string | null;
  confidence: number; // 0–1, render as a gradient, not a binary
  grounded: boolean;
}

export interface CollateralPair {
  organism: string;
  drug_a: string;
  drug_b: string;
  reciprocal: boolean;
  strength?: number | null;
  n_lineages?: number | null;
}

// Graph view payloads
export interface LineageNode {
  id: string;
  label: string;
  parent_id?: string | null;
  flipper_count: number;
  // Optional enrichment for the hover card (additive — safe to ignore).
  st?: string | number | null;
  year?: string | number | null;
  country?: string | null;
  lineage?: string | null; // BurkData: experimental lineage membership, e.g. "L1, L2"
  founder?: boolean | null;
}
export interface LineageGraph {
  nodes: LineageNode[];
  edges: { source: string; target: string }[];
}

// A flipper gene carried by a strain (from /api/graph/strain).
export interface StrainGene {
  locus_tag: string;
  gene_symbol?: string | null;
  product?: string | null;
  chrom?: string | null;
  indel_delta?: number | null;
  flipper_support?: number | null;
  is_flipper: boolean;
  effect?: string | null;
  wp?: string | null;
}
export interface StrainDetail {
  strain: {
    id: string;
    external_id: string;
    label: string;
    source: string;
    metadata: Record<string, unknown>;
  } | null;
  genes: StrainGene[];
}

// Evidence subgraph for a gene (from /api/graph/evidence). Mirrors graph_shaping.shape_evidence.
export interface EvidenceProvenance {
  pmid?: string | null;
  pubmed_url?: string | null;
  db?: string | null; // 'CARD' | 'UniProt' | ...
  acc?: string | null; // 'ARO:3003378' | UniProt accession
  ref_url?: string | null;
  paper_title?: string | null;
  paper_year?: number | null;
}
// One step in an edge's provenance chain. `actor` marks the deterministic-vs-LLM seam.
export interface EvidenceTraceStep {
  step: string; // 'extracted' | 'grounded' | 'not_grounded' | 'scored'
  actor: "llm" | "deterministic";
  label: string;
  detail?: string | null;
  source?: string | null;
  url?: string | null;
  by?: string | null; // e.g. 'ai/extraction.py@claude-sonnet-5'
}
export interface EvidenceEdgeView {
  id?: string | null;
  relation: Relation;
  target?: string | null;
  target_type?: NodeType | null;
  confidence: number; // 0–1, render as a gradient
  grounded: boolean;
  subject?: string | null;
  object_kind?: string | null;
  evidence_span?: string | null;
  claim?: string | null; // composed subject+relation+object sentence
  extracted_by?: string | null;
  grounding_reason?: string | null;
  trace?: EvidenceTraceStep[]; // ordered provenance chain (Slice 2)
  provenance: EvidenceProvenance;
}
export interface EvidenceSubgraph {
  gene: { id?: string | null; locus_tag: string; symbol?: string | null; product?: string | null };
  edges: EvidenceEdgeView[];
  counts: { total: number; grounded: number };
}

// Ranked candidate targets for a strain (from /api/targets). Mirrors targets_shaping.
export interface TargetTractability {
  source?: string; // 'ChEMBL'
  assessed: boolean;
  has_target?: boolean;
  chembl_target_id?: string | null;
  queried_acc?: string | null;
  n_bioactivities?: number;
  n_compounds?: number;
  max_pchembl?: number | null;
  bucket?: string | null; // 'novel' | 'precedented' | 'some-chemical-matter' | ...
  mechanisms?: { molecule_chembl_id?: string; mechanism_of_action?: string; action_type?: string }[];
  note?: string | null;
}
export interface TargetScoreComponents {
  evidence?: number;
  flipper?: number;
  n_edges?: number;
  grounded_edges?: number;
  mean_confidence?: number;
  flipper_support?: number;
}
export interface RankedTarget {
  id?: string | null;
  gene_id?: string | null;
  locus_tag?: string | null;
  name?: string | null;
  product?: string | null;
  mechanism?: string | null;
  rank_score?: number | null; // 0–1, render as a bar
  score_components: TargetScoreComponents;
  tractability: TargetTractability;
  evidence: EvidenceEdgeView[];
  evidence_counts: { total: number; grounded: number };
  structure: { locus_tag?: string | null; wp?: string | null; available: boolean };
  in_strain: boolean;
  strain_flipper: boolean;
  rationale: string;
  rationale_citations: string[];
  rationale_source: "deterministic" | "llm" | "cached";
  rationale_model?: string | null; // model id when rationale_source is "cached"/"llm"
}
export interface TargetsResponse {
  strain: { id: string; label: string } | null;
  organism: string;
  targets: RankedTarget[];
  counts: { targets: number; with_structure: number };
}

// Antibiotic cycling proposal (from /api/treatment/cycle). Mirrors treatment_shaping.
export interface CycleStep {
  from: string;
  to: string;
  reciprocal: boolean;
  n_lineages?: number | null;
  strength?: number | null;
  closes_loop: boolean;
}
export interface RcsPair {
  drug_a: string;
  drug_b: string;
  reciprocal: boolean;
  n_lineages?: number | null;
  strength?: number | null;
}
export interface CycleNarrative {
  summary?: string | null;
  caveats: string[];
  citations: string[];
  source?: "cached" | "llm" | null;
}
export interface CycleResponse {
  organism: string;
  cycle: string[];
  summary: string; // deterministic one-liner (no LLM)
  steps: CycleStep[];
  rcs_pairs: RcsPair[];
  narrative: CycleNarrative | null; // cached by default, or live when narrate=true
  narrative_source?: "cached" | "llm" | null;
  is_hypothesis: boolean; // always true
  caveats: string[];
  counts: { pairs: number; reciprocal: number; cycle_length: number };
}

// Retrieved counterfactual: what real lineages did after a resistance event
// (from /api/trajectory). RETRIEVAL over real data — never predicted/generated.
export interface ObservedNext {
  sensitized_to: string; // drug that became viable again
  n_lineages: number;
  n_strains: number;
  backing_strains: string[]; // real strain external ids
  lineages: string[];
}
export interface TrajectoryEvidence {
  organism: string;
  resisted: string;
  event_strain?: string | null;
  observed_next: ObservedNext[];
  support_lineages: number;
  backing_strains: string[];
  sufficient: boolean; // false → honest "insufficient real evidence" state
  kind: "retrieved"; // never 'predicted'/'generated'
  note?: string | null;
  provenance: Record<string, unknown>;
  // Attached by the API (Slice 3): narration of the RETRIEVED trajectory.
  narrative?: TrajectoryNarrative | null;
  narrative_source?: "cached" | "llm" | null;
}
export interface TrajectoryNarrative {
  summary?: string | null;
  citations: string[];
  source?: "cached" | "llm" | null;
}

// Predicted / experimental 3D structure for a gene (from /api/structure).
export interface StructureResult {
  locus_tag: string;
  wp?: string | null;
  name?: string | null;
  product?: string | null;
  source: "alphafold" | "alphafold_pending" | "rcsb" | "unavailable";
  pdb: string | null;
  plddt?: number | null;
  residue_count?: number | null;
  pdb_id?: string | null;
  ptm?: number | null;
  avg_plddt?: number | null;
  status: string;
  note?: string | null;
}
