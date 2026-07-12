# CLAUDE.md — Achilles

Operating brief for Claude Code. Read this fully before writing any code.

## What this is

Achilles is an AI-native database and web app for **antimicrobial resistance (AMR)
target identification and treatment optimization**. Think "Nextstrain for the
experimental record": Nextstrain stops at how strains are phylogenetically related.
Achilles continues the chain — strain -> variant -> mechanism -> candidate target ->
literature evidence — with provenance on every link, and turns reversible
("flipper") mutation structure into evidence-backed antibiotic-cycling suggestions.

Primary user: an AMR researcher (academic or translational) tracking resistance
across bacterial strains.

## The one idea that governs everything

**The product is the graph, not the pipeline or the viz.** The core object is
`evidence_edges`: `(source_node, relation, target_node, provenance, confidence)`.
Provenance is NEVER null — every edge points to a PMID or a reference-DB accession
(CARD / UniProt). If a claim can't be grounded, it does not become an edge.

## Non-negotiable design principles

1. **Deterministic core, LLM on top.** Parsing, lineage/flipper detection, and the
   collateral-sensitivity / cycling math are computed in plain Python — never by an
   LLM. Claude is used only for (a) extracting typed claims from literature and
   (b) narrating/ranking with citations. Claude must never invent a valuation, a
   cycling schedule, or a numeric result.
2. **Provenance or it doesn't exist.** See above. Grounding kills unsupported claims.
3. **Preserve contracts.** The Pydantic models in `backend/app/models/` and the TS
   types in `frontend/src/lib/types.ts` are the contract between layers. When you
   extend, add fields — don't break existing shapes. Keep the two in sync.
4. **Confidence gradients, not binary cutoffs.** Edges and rankings carry a 0–1
   confidence, surfaced in the UI as a gradient, not a hard yes/no.
5. **Team/data hygiene.** Only public data (NCBI Pathogen Detection, BV-BRC, CARD,
   UniProt, Europe PMC) or data the user is cleared to release. The repo is MIT and
   must stay clean of any non-redistributable dataset.

## Architecture (data flows top-down)

```
public data + strains  ->  ingestion (FastAPI, deterministic)  ->  Postgres graph
   (NCBI/BV-BRC/CARD/         parse · lineage · flipper detect        (+ pgvector)
    Europe PMC)                                                            |
                                                                           v
                        AI reasoning layer (Claude): extract · ground · rank · optimize
                                                                           |
                                                                           v
                              Next.js web app: lineage tree · target graph ·
                                       evidence panel · cycling view
```

## Build sequence — spine first, each phase ships

Work in this order. Each phase must leave the app runnable and the contracts intact.

- **Phase 0 (scaffolded here):** repo, schema, config, deploy wiring, module stubs.
  Get `docker compose up` + `make dev` to a hello-world round trip.
- **Phase 1 — data in, tree out:** implement `sources/` adapters for one organism,
  `ingestion/parsers.py`, `ingestion/lineage.py`, `ingestion/flippers.py`; render a
  real interactive lineage tree in the frontend from `/api/graph/lineage`.
- **Phase 2 — literature -> grounded edges:** `sources/europepmc.py` fetch ->
  `ai/extraction.py` typed claims -> `ai/grounding.py` validate vs CARD/UniProt ->
  edges land in `evidence_edges` with provenance. Embed papers into pgvector.
- **Phase 3 — linking + target ranking:** `ai/targets.py` ranks candidate targets for
  a strain/variant with evidence chains; `/api/targets` + target graph view.
- **Phase 4 — treatment optimization:** `ingestion/collateral.py` computes CS/RCS
  structure deterministically; `ai/treatment.py` narrates a cycling suggestion with
  citations; cycling view.
- **Phase 5 — polish:** protein-structure beat (Mol* on a PDB/AlphaFold entry),
  exports, reproducibility (seeded demo dataset a judge can run end to end).

## Conventions

- Python 3.11+, FastAPI, SQLAlchemy 2.x (async), Pydantic v2, `ruff` + `black`.
- Genomic parsing: `cyvcf2`/`pysam` for VCF, `polars` for tabular. Deterministic —
  no network, no LLM in `ingestion/`.
- Anthropic: use `backend/app/ai/client.py`. Models are config-driven
  (`settings.model_extract`, `settings.model_reason`) — never hard-code a model ID in
  a module. Current defaults: `claude-sonnet-5` for extraction, `claude-opus-4-8` for
  reasoning. Every AI call returns structured JSON that is parsed and validated
  against a Pydantic model before use.
- Frontend: Next.js (App Router) + TypeScript + Tailwind. Viz: D3 for the lineage
  tree, Cytoscape.js or react-force-graph for the target graph, Mol* for structures.
- Keep `frontend/src/lib/types.ts` a mirror of `backend/app/models/`.

## What NOT to do

- Don't let an LLM compute numbers, schedules, or valuations.
- Don't write an edge without provenance.
- Don't copy prior thesis code — implement fresh here.
- Don't break an existing Pydantic/TS shape; extend it.
- Don't add a dataset that isn't public or cleared.

## Where to start reading

`db/schema.sql` (the spine) -> `backend/app/models/` -> `backend/app/ai/prompts.py`
-> this file's build sequence. Then begin Phase 1.
