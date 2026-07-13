# Drive B — populate a second real domain (Pseudomonas aeruginosa)

Goal: take the *Pseudomonas aeruginosa* domain from **scaffold** to a **grounded graph**, so
"domain-agnostic" is demonstrated on a second organism with real, cited data — not claimed.

**Hard rule:** every grounded identifier (reference-gene accession, PMID, CARD/UniProt
accession) must be looked up from a public source. Nothing is invented. If you can't fetch
it, it doesn't go in.

These steps need **network + an `ANTHROPIC_API_KEY`** and run on your machine (the build
sandbox has neither). What's already wired is marked ✅; what you run is marked ▶.

## 0. Prereqs
```bash
cd backend && cp .env.example .env   # set ANTHROPIC_API_KEY (+ DATABASE_URL for seeding)
```

## 1. Domain is registered ✅
`Pseudomonas aeruginosa` is in `app/ingestion/domains.py` with its real PubMLST database and
the Curran-2004 7-locus scheme (`acsA aroE guaA mutL nuoD ppsA trpE`) and a Europe PMC query.
`GET /api/domains` reports it as a scaffold (`ready:false`) until steps 2–3 are done.

## 2. Fetch real isolates ▶
```bash
make fetch-domain DOMAIN=pseudomonas   # → data/demo/paeruginosa_pubmlst.json
```
This pulls real, dated PubMLST isolates with full MLST profiles (uses the domain's DB + loci).

## 3. Populate the reference-gene catalog ▶ (real accessions only)
Look up 5–8 well-characterised P. aeruginosa efflux/regulator genes and paste their **real**
locus tags + products (+ `WP_`/UniProt accessions) into `PSEUDOMONAS.reference_genes`:

- UniProt (protein + accession), organism id 208964 (PAO1). Example query:
  `https://www.uniprot.org/uniprotkb?query=gene:mexR%20AND%20organism_id:208964`
  Good candidates: **mexR, mexA, mexB, oprM, nalC, nalD, nfxB, mexZ**.
- NCBI Gene / RefSeq for the PAO1 locus tag (e.g. `PA...`) and `WP_` protein accession:
  `https://www.ncbi.nlm.nih.gov/gene/?term=mexB+Pseudomonas+aeruginosa+PAO1`

Each entry: `{"locus_tag": "<real>", "name": "<gene>", "wp": "<WP_... or null>", "product": "<real>"}`.
Do **not** guess an accession — copy it from the page.

## 4. Build the grounded literature corpus ▶
```bash
cd backend && python -m app.sources.make_literature_snapshot --domain pseudomonas
# → data/demo/literature/pseudomonas_corpus.json
```
✅ The corpus builder is domain-parameterized (`_corpus_for_domain`): it derives per-gene
Europe PMC queries + topic filters from the reference catalog, extracts typed claims, and
grounds them against CARD/UniProt — same pipeline as Burkholderia. It refuses to run on an
empty catalog (step 3 gates it), so nothing is fabricated.

## 5. Seed it ▶ — remaining wiring
The **deterministic core is already organism-agnostic** and the fetch/corpus paths are wired.
The last mile is generalising two seed entry points to take a `DomainConfig` (they currently
default to Burkholderia), so the second domain's lineage + grounded edges land in the DB:

- `app/ingestion/seed.py::_seed_public` — parameterize `SNAPSHOT`, `ORGANISM`, and the
  gene-id function by domain (organism + reference genes already come from the registry).
- `app/ingestion/seed_literature.py` — read `<domain>_corpus.json` and bind edges via the
  domain's gene-id (it currently hard-codes `_burk_gene_id`).

Ask me to do this generalisation and I'll wire `make seed DOMAIN=pseudomonas` end to end
(kept separate so the shipped Burkholderia seed stays byte-identical and green).

## 6. Verify ▶
```bash
curl localhost:8000/api/domains                                   # pseudomonas ready:true
curl "localhost:8000/api/graph/lineage?organism=Pseudomonas%20aeruginosa"   # nodes returned
curl "localhost:8000/api/validation?organism=Pseudomonas%20aeruginosa"      # recall/refusal
```

## Status
✅ registry · ✅ isolate fetch · ✅ domain-parameterized corpus builder (tested)
▶ your part: reference-gene lookup + corpus build (network/LLM)
⏳ remaining: seed generalisation (step 5) — ask and I'll wire it
