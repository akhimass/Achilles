-- Achilles schema — the spine of the product.
-- The node tables are ordinary. The product is `evidence_edges`.
-- Requires: Postgres 15+ with the pgvector extension.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Node tables ──────────────────────────────────────────────────────────────

-- A bacterial strain / isolate (from BV-BRC, NCBI Pathogen Detection, or user data).
CREATE TABLE strains (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id   TEXT NOT NULL,                 -- e.g. BV-BRC genome id, NCBI accession
    source        TEXT NOT NULL,                 -- 'bvbrc' | 'ncbi_pathogen' | 'user'
    organism      TEXT NOT NULL,                 -- e.g. 'Burkholderia multivorans'
    label         TEXT,                          -- human label, e.g. strain '149'
    parent_id     UUID REFERENCES strains(id),   -- lineage edge for the tree
    metadata      JSONB NOT NULL DEFAULT '{}',   -- collection date, phenotype, etc.
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, external_id)
);
CREATE INDEX ON strains (organism);
CREATE INDEX ON strains (parent_id);

-- A gene / locus (from reference annotation). Defined before `variants` so the FK resolves.
CREATE TABLE genes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locus_tag     TEXT NOT NULL,                 -- e.g. A8H40_RS24255
    name          TEXT,                          -- gene symbol if known
    product       TEXT,                          -- protein product description
    uniprot_acc   TEXT,                          -- UniProt accession if resolved
    organism      TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}',
    UNIQUE (organism, locus_tag)
);
CREATE INDEX ON genes (uniprot_acc);

-- A genomic variant (SNP or indel) called against a reference, tied to a strain.
CREATE TABLE variants (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strain_id     UUID NOT NULL REFERENCES strains(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL,                 -- 'snp' | 'indel'
    ref_position  BIGINT NOT NULL,               -- position on the reference
    ref_allele    TEXT,
    alt_allele    TEXT,
    gene_id       UUID REFERENCES genes(id),     -- filled by annotation (nullable)
    effect        TEXT,                          -- 'synonymous' | 'nonsynonymous' | 'frameshift' | 'intergenic'
    allele_freq   REAL,                          -- 0–1, read-level support
    is_flipper    BOOLEAN NOT NULL DEFAULT FALSE, -- reversible across the lineage
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (strain_id, kind, ref_position, alt_allele)
);
CREATE INDEX ON variants (strain_id);
CREATE INDEX ON variants (ref_position);
CREATE INDEX ON variants (is_flipper) WHERE is_flipper;

-- A candidate therapeutic target (a gene/protein a drug could act on, or a
-- collateral-sensitivity vulnerability). Distinct from `genes`: a target is a gene
-- promoted to "worth acting on", with tractability evidence.
CREATE TABLE targets (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gene_id       UUID NOT NULL REFERENCES genes(id) ON DELETE CASCADE,
    mechanism     TEXT,                          -- e.g. 'efflux', 'stringent response'
    tractability  JSONB NOT NULL DEFAULT '{}',   -- ChEMBL/known-inhibitor evidence
    pdb_ids       TEXT[] DEFAULT '{}',           -- structures for the 3D beat
    rank_score    REAL,                          -- 0–1, filled by ai/targets.py
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON targets (gene_id);

-- A paper / literature source. Embedded into pgvector for RAG retrieval.
CREATE TABLE papers (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pmid          TEXT UNIQUE,                   -- PubMed id
    doi           TEXT,
    title         TEXT NOT NULL,
    abstract      TEXT,
    year          INT,
    source        TEXT NOT NULL DEFAULT 'europepmc',
    embedding     VECTOR(1024),                  -- set embedding dim in config
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON papers USING hnsw (embedding vector_cosine_ops);

-- ─── The product: the evidence graph ─────────────────────────────────────────
-- Every meaningful relationship is an edge, and every edge carries provenance.
-- This table is why Achilles is more than a phylogeny viewer.

CREATE TABLE evidence_edges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type     TEXT NOT NULL,               -- 'variant' | 'gene' | 'target' | 'strain'
    source_id       UUID NOT NULL,
    relation        TEXT NOT NULL,               -- 'confers_resistance' | 'sensitizes_to' |
                                                 -- 'is_target_of' | 'implicates' | 'reverts_with' ...
    target_type     TEXT NOT NULL,               -- 'target' | 'gene' | 'drug' | 'mechanism'
    target_id       UUID,                        -- nullable when target is a literal (e.g. drug name)
    target_literal  TEXT,                        -- e.g. drug name / mechanism string
    -- Provenance is NEVER both-null. Exactly one of pmid / ref_db_acc must be set.
    provenance_pmid TEXT REFERENCES papers(pmid),
    provenance_db   TEXT,                        -- 'CARD' | 'UniProt' | 'ChEMBL'
    provenance_acc  TEXT,                        -- accession within that DB
    confidence      REAL NOT NULL,               -- 0–1
    extracted_by    TEXT,                        -- 'ai/extraction.py@<model>' or 'ingestion'
    grounded        BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT provenance_present CHECK (
        provenance_pmid IS NOT NULL OR provenance_acc IS NOT NULL
    ),
    CONSTRAINT confidence_range CHECK (confidence >= 0 AND confidence <= 1)
);
CREATE INDEX ON evidence_edges (source_type, source_id);
CREATE INDEX ON evidence_edges (target_type, target_id);
CREATE INDEX ON evidence_edges (relation);
CREATE INDEX ON evidence_edges (grounded) WHERE grounded;

-- ─── Collateral sensitivity (deterministic, computed) ────────────────────────
-- Pairwise CS/RCS relationships between antibiotics for a given lineage context.
-- Populated by ingestion/collateral.py — never by an LLM.

CREATE TABLE collateral_sensitivity (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organism      TEXT NOT NULL,
    drug_a        TEXT NOT NULL,                 -- resistance acquired to A ...
    drug_b        TEXT NOT NULL,                 -- ... induces sensitivity to B
    reciprocal    BOOLEAN NOT NULL DEFAULT FALSE, -- true if B->A also holds (RCS)
    strength      REAL,                          -- effect size / support
    n_lineages    INT,                           -- how many lineages support it
    metadata      JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organism, drug_a, drug_b)
);
CREATE INDEX ON collateral_sensitivity (organism);
CREATE INDEX ON collateral_sensitivity (reciprocal) WHERE reciprocal;
