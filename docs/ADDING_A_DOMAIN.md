# Adding a domain

Achilles is a domain-agnostic evidence-graph pipeline. The antimicrobial-resistance
(Burkholderia) work is one **worked example**, registered in
`backend/app/ingestion/domains.py` alongside a second, scaffolded domain
(*Pseudomonas aeruginosa*). Adding a domain is a config entry plus its **real, fetched**
data — never a code fork, and never fabricated identifiers.

## The one rule

Everything grounded must be a **real public identifier**: PubMLST isolates, NCBI locus
tags / RefSeq `WP_` accessions, UniProt accessions, PMIDs, CARD/UniProt/ChEMBL
accessions. If you can't fetch it, it doesn't go in. A wrong accession is exactly the kind
of ungrounded claim the whole product is built to refuse.

## What a domain is

A `DomainConfig` (see `domains.py`) carries:

- `organism`, `pubmlst_isolates_db`, `mlst_loci` — the lineage source (public).
- `reference_genes` — real NCBI locus tags + products (+ `WP_`/UniProt accessions).
- `europepmc_query` — how its literature corpus is pulled.
- `pubmlst_snapshot` / `corpus` / `benchmark` — committed data artifacts.
- `ready` — true only when it can seed a real graph offline (snapshot + reference genes).

`GET /api/domains` reports every registered domain and whether it's `ready` or still a
scaffold — honestly.

## Steps to bring a domain online

1. **Register it** in `domains.py` with its real PubMLST db + MLST scheme and a literature
   query. Leave `reference_genes=()` until you have real accessions.

2. **Fetch its lineage** (needs network — run locally):

   ```bash
   cd backend && python -m app.sources.fetch_domain <domain_key> --limit 60
   ```

   This writes `data/demo/<snapshot>.json` from real, dated PubMLST isolates.

3. **Populate the reference-gene catalog** from NCBI/UniProt for that organism's
   resistance/regulator genes (real locus tags + `WP_`/UniProt accessions). Put them in the
   domain's `reference_genes`. Do not invent accessions — look them up.

4. **Build the literature corpus** (Europe PMC → typed claims → grounded against
   CARD/UniProt) using the domain's `europepmc_query`, and a small benchmark of known-true
   / known-false relationships for self-validation.

5. **Seed** it. Once `ready` is true, the same deterministic core seeds its lineage +
   grounded graph exactly as it does for Burkholderia.

The deterministic core (lineage MST + flipper detection) is already organism-agnostic —
proven in `tests/test_generalization.py` and live via the console's "Bring your own data".
This doc is about giving a domain its *grounded* graph, which requires real data, fetched.
