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
export interface CsProvenance {
  pmid: string;
  pubmed_url: string;
  doi?: string | null;
  source?: string | null;
  tier?: string | null;
}
export interface CycleStep {
  from: string;
  to: string;
  reciprocal: boolean;
  n_lineages?: number | null;
  strength?: number | null;
  provenance?: CsProvenance | null;
  closes_loop: boolean;
}
export interface RcsPair {
  drug_a: string;
  drug_b: string;
  reciprocal: boolean;
  n_lineages?: number | null;
  strength?: number | null;
  provenance?: CsProvenance | null;
}
export interface CycleAnchor {
  anchored: boolean;
  strain?: string | null;
  requested: string[];
  matched: string[];
  unmatched: string[];
  reason: string;
}
export interface CycleNarrative {
  summary?: string | null;
  caveats: string[];
  citations: string[];
  source?: "cached" | "llm" | null;
}
export interface NextExperiment {
  drug_a: string;
  drug_b: string;
  n_lineages: number;
  provenance?: CsProvenance | null;
  headline: string;
  detail: string;
}
export interface CycleResponse {
  organism: string;
  cycle: string[];
  summary: string; // deterministic one-liner (no LLM)
  steps: CycleStep[];
  rcs_pairs: RcsPair[];
  anchor?: CycleAnchor | null; // strain/drug the cycle was anchored to (if any)
  narrative: CycleNarrative | null; // cached by default, or live when narrate=true
  narrative_source?: "cached" | "llm" | null;
  next_experiment?: NextExperiment | null; // deterministic single wet-lab next step
  is_hypothesis: boolean; // always true
  caveats: string[];
  counts: { pairs: number; reciprocal: number; cited: number; cycle_length: number };
}

// Bring-your-own-strains result (from /api/ingest/upload) — a LineageGraph + summary.
export interface UploadSummary {
  organism: string;
  strains: number;
  loci: number;
  flipper_carrying: number;
  max_flipper: number;
  roots: number;
  warnings?: { dropped_rows?: number };
}
export interface UploadResult extends LineageGraph {
  summary: UploadSummary;
}

// Docking / druggability (from /api/docking) — cited inhibitor + Tamarind results.
export interface DockingLigand {
  name?: string | null;
  smiles?: string | null;
  pubchem_cid?: number | null;
  pubchem_url?: string | null;
  role?: string | null;
  citation?: string | null;
  note?: string | null;
}
export interface DockingTarget {
  locus: string;
  ligands: DockingLigand[];
  admet?: { source_file?: string | null; properties?: Record<string, unknown> } | null;
  docking?: { pose_available?: boolean; pose_file?: string | null; score?: number | null } | null;
  status: "ready" | "properties_only" | "docked";
  runner: string;
}
export interface DockingResponse {
  targets: DockingTarget[];
  counts: { with_ligand: number; docked: number };
}

// Self-validation ("prove-it") — the engine checked against public ground truth.
export interface ValidationItem {
  gene: string;
  locus: string;
  relation: string;
  target_terms: string[];
  kind: "positive" | "negative";
  status:
    | "recovered"
    | "literature_only"
    | "missing"
    | "refused"
    | "fabricated"
    | "weakly_asserted";
  matched_target?: string | null;
  grounded: boolean;
  provenance: {
    pmid?: string | null;
    pubmed_url?: string | null;
    db?: string | null;
    acc?: string | null;
    ref_url?: string | null;
  };
  expected_citation?: string | null;
  note?: string | null;
}
export interface ValidationReport {
  organism: string;
  items: ValidationItem[];
  metrics: {
    positives: number;
    recovered: number;
    literature_only: number;
    missing: number;
    recovery_rate: number;
    negatives: number;
    refused: number;
    fabricated: number;
    weakly_asserted: number;
    clean: boolean;
  };
}

// Retrodiction — time-split foresight over the grounded graph (from /api/validation/retrodiction).
export type RetroStatus =
  | "known_by_cutoff"
  | "anticipated_drug"
  | "anticipated_mechanism"
  | "not_anticipable"
  | "unconfirmed";
export interface RetroSignal {
  relation?: string | null;
  target?: string | null;
  year?: number | null;
  grounded?: boolean;
  provenance?: {
    pmid?: string | null;
    pubmed_url?: string | null;
    db?: string | null;
    acc?: string | null;
    ref_url?: string | null;
  };
}
export interface RetroPositive {
  gene: string;
  locus: string;
  relation: string;
  target_terms: string[];
  citation?: string | null;
  note?: string | null;
  status: RetroStatus;
  confirm_year: number | null;
  confirming_edge: RetroSignal | null;
  pre_cutoff_signal: RetroSignal[];
}
export interface RetrodictionReport {
  organism: string;
  cutoff: number;
  metrics: {
    cutoff: number;
    positives: number;
    known_by_cutoff: number;
    held_out: number;
    anticipated: number;
    anticipated_drug: number;
    anticipated_mechanism: number;
    not_anticipable: number;
    unconfirmed: number;
    anticipation_rate: number;
    false_anticipations: number;
    clean: boolean;
  };
  positives: RetroPositive[];
  false_anticipated: { gene: string; locus: string; target_terms: string[] }[];
}

// Grounded Q&A (from /api/ask) — answers only from cited graph evidence, or refuses.
export interface AskProvenance {
  pmid?: string | null;
  pubmed_url?: string | null;
  db?: string | null;
  acc?: string | null;
  ref_url?: string | null;
}
export interface AskClaim {
  kind: "paper" | "gene" | "edge";
  title?: string | null;
  snippet?: string | null;
  relation?: string | null;
  gene_locus?: string | null;
  confidence?: number | null;
  grounded: boolean;
  score?: number | null;
  provenance: AskProvenance;
  citation?: string | null;
}
export interface AskSynthesis {
  summary: string;
  citations: string[];
  caveats: string[];
  refused: boolean;
  source: "llm";
}
export type AskPersona = "researcher" | "physician" | "computational";
export interface AskResponse {
  question: string;
  persona: AskPersona;
  intent: "treatment" | "target" | "provenance" | "mechanism" | "general";
  grounded: boolean;
  refused: boolean;
  claims: AskClaim[];
  deterministic_summary: string;
  caveats: string[];
  answer: AskSynthesis | null;
  counts: { claims: number; grounded: number; retrieved: number };
}

// Audit (from /api/audit) — tamper-evident, re-verifiable ledger over the prove-it result.
export interface AuditEntry {
  index: number;
  kind: string;
  gene: string;
  locus?: string | null;
  relation?: string | null;
  target_terms: string[];
  verdict: string;
  grounded: boolean;
  citation?: string | null;
  prev_hash: string;
  entry_hash: string;
}
export interface AuditReport {
  organism: string;
  algorithm: string;
  metrics: ValidationReport["metrics"];
  entries: number;
  head: string;
  ledger: AuditEntry[];
}
export interface AuditVerify {
  valid: boolean;
  checked: number;
  break_at: number | null;
  head: string;
}

// Bridge (from /api/bridge) — one grounded finding, translated researcher → physician.
export interface BridgeCitation {
  label: string;
  url?: string | null;
}
export interface BridgeClaim {
  relation: string;
  target: string;
  citation: BridgeCitation;
}
export interface BridgeResearch {
  lens: string;
  gene: { locus?: string | null; name?: string | null; product?: string | null };
  mechanism: string[];
  summary: string;
  target: {
    rank_score?: number | null;
    tractability_bucket?: string | null;
    structure_available?: boolean;
  } | null;
  grounded_claims: BridgeClaim[];
}
export interface BridgeClinic {
  lens: string;
  drives_resistance_to: string[];
  collateral_opening: { drug_a: string; drug_b: string; citation: BridgeCitation } | null;
  cited_cycle: { cycle: string[]; summary?: string | null } | null;
  actionable: string;
  caveats: string[];
}
export interface BridgeResponse {
  organism: string;
  found: boolean;
  reason?: string;
  gene: { locus?: string | null; name?: string | null; product?: string | null };
  research?: BridgeResearch;
  clinic?: BridgeClinic;
  handoff?: string;
  provenance_carried?: number;
}

// Red-team verdict — a judge-typed claim adjudicated against the grounded graph.
export interface RedTeamVerdict {
  claim: {
    gene?: string | null;
    locus?: string | null;
    relation?: string | null;
    target?: string | null;
  };
  verdict: "supported" | "weak" | "refused" | "unknown_gene";
  grounded: boolean;
  matched_target?: string | null;
  matched_relation?: string | null;
  provenance?: {
    pmid?: string | null;
    pubmed_url?: string | null;
    db?: string | null;
    acc?: string | null;
    ref_url?: string | null;
  };
  reason: string;
}

// Grounded search over the evidence graph (from /api/search).
export interface SearchResult {
  kind: "paper" | "gene" | "edge";
  id?: string | null;
  title?: string | null;
  snippet?: string | null;
  score: number;
  grounded: boolean;
  provenance: {
    pmid?: string | null;
    pubmed_url?: string | null;
    db?: string | null;
    acc?: string | null;
    ref_url?: string | null;
  };
  extra: Record<string, unknown>;
  semantic_similarity?: number | null;
}
export interface SearchResponse {
  query: string;
  mode: "lexical" | "semantic";
  results: SearchResult[];
  counts: { total: number; grounded: number; by_kind: Record<string, number> };
}

// Retrieved counterfactual: what real lineages did after a resistance event
// (from /api/trajectory). RETRIEVAL over real data — never predicted/generated.
export interface ObservedNext {
  sensitized_to: string; // drug that became viable again
  n_lineages: number;
  n_strains: number;
  backing_strains: string[]; // real strain external ids
  lineages: string[];
  reciprocal: boolean; // reverse also observed → cycle-eligible reversible target
}
export interface TrajectoryEvidence {
  organism: string;
  resisted: string;
  event_strain?: string | null;
  observed_next: ObservedNext[];
  support_lineages: number;
  backing_strains: string[];
  reciprocal_count: number; // observed_next that are reciprocal (feed the cycle)
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
