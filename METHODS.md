# Methods

Achilles builds a provenance-checked evidence graph from public data. The governing
principle: a **deterministic engine** computes everything quantitative, and the language
model is confined to two jobs — extracting typed claims from literature and narrating
already-computed results with citations. It never invents a number, a score, or a
schedule. If a claim can't be grounded, it does not become an edge.

A live version of this page is at `/methods`.

## 1. The object — the reversible target

Most target-ID tools name a gene *associated* with resistance. Achilles names the
vulnerability resistance *creates* — the reversible ("flipper") target collateral
sensitivity opens — grounded in what real evolved lineages did next. The core object is an
evidence edge: `(source, relation, target, provenance, confidence)`. Provenance is never
null.

## 2. Deterministic core (no LLM)

Lineage reconstruction (minimum-spanning tree over allelic distance), flipper detection
(allele-reversal along lineage paths), the target rank score, and the collateral-
sensitivity / cycling math are plain, unit-tested Python — same input, same output, no
model calls. The core is organism-agnostic (verified by a generalization test on a
non-Burkholderia scheme) and powers "bring your own data".

## 3. The LLM's two bounded jobs

- **Extraction** — from a single public abstract, typed claims `(subject, relation,
  object, evidence_span, confidence)` using only that text.
- **Narration** — a short, cited explanation of already-computed results.

Every model call returns JSON validated against a Pydantic schema before use; prompts
forbid outside knowledge and forbid computing numbers.

## 4. Grounding — cite or it doesn't exist

Each extracted claim is checked against reference-database facts (CARD/ARO, UniProt,
ChEMBL). It becomes a **grounded** edge only if a reference fact corroborates it, carrying
that accession; a claim supported only by an abstract is kept **abstract-only** (visually
distinct, never shown as validated). Accessions are never invented.

## 5. Validation — recall, adversarial refusal, zero fabrication

Held to 29 independent, publicly-cited controls: **recover** every established
relationship from a grounded edge (recall), and **refuse** an adversarial battery of
plausible-but-false claims (the traps a hallucinating model falls for — e.g.
MarR→vancomycin, efflux→isoniazid, a regulator posed as a carbapenem target). The
fabrication count must be **zero**. Computed live; a **red-team** box adjudicates any
user-typed claim (supported-with-citation, or refused).

Current: **12/12 recovered · 17/17 adversarial refused · 0 fabricated.**

## 6. Retrodiction — foresight, not just recall

Freeze the literature at a cutoff year, hide everything after, and measure how many
later-confirmed relationships the pre-cutoff graph already pointed at. Anticipation is
graded (drug-level > mechanism-level); honest "not anticipable" is reported when there is
no pre-cutoff signal; and **no false claim is ever anticipated**.

## 7. Treatment optimization — a hypothesis, never advice

The antibiotic-cycling suggestion is walked deterministically over a reciprocal
collateral-sensitivity graph; the public pairs are cited to the literature
(PMID 32335276); the model only narrates it. Framed everywhere as a **research
hypothesis** — no PK/dosing/toxicity/in-vivo is modeled; not a treatment recommendation.

## 8. Reproducibility

The public evidence graph rebuilds offline from a committed corpus — no live API to seed.
All sources are public (PubMLST, Europe PMC, CARD/ARO, UniProt, ChEMBL, NCBI, AlphaFold via
Tamarind, RCSB). MIT.

```bash
make db            # Postgres + pgvector
make seed-public   # PubMLST + committed public caches (no private data)
make backend       # FastAPI  :8000
make frontend      # Next.js  :3000
```

## 9. Limitations

- The control set is small relative to a large-N benchmark; the strength is the *property*
  (recall + adversarial refusal + zero fabrication) and the live red-team, not raw count.
- A second domain (Pseudomonas aeruginosa) is **scaffolded** — the pipeline is wired
  (see `DRIVE_B.md`), but its grounded gene/literature data must be fetched, not assumed.
- Docking shows a cited inhibitor **ready to dock**; a computed pose requires a Tamarind
  run. No pose is fabricated.
- Lineage is a deterministic reconstruction from allelic distance, not a validated
  phylogeny; collateral sensitivity is frequently non-reciprocal and strain-specific.
