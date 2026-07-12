# Achilles — submission

## Links

- **Live app (public):** https://achilles-science.vercel.app
- **API:** https://achilles-production-2565.up.railway.app
- **Repo:** https://github.com/akhimass/Achilles (MIT)

> Use `achilles-science.vercel.app` — the `*-akhimass-projects.vercel.app` deployment URLs
> are team-scoped and sit behind Vercel login; the clean domain is public.

## Blurb (~200 words)

**Achilles** turns discovery into an evidence graph you can't fake. Point it at your data
and it builds a provenance-checked graph where every claim carries a citation — a
deterministic core does the math, and the language model only reads, retrieves, and cites.
Its edge is verifiability you can break on stage: type a false claim and watch it refuse.
It recovers known biology (**9/9**), refuses planted falsehoods (**4/4**), and fabricates
nothing (**0**). On a time-split hold-out it goes further — **anticipating** relationships
before the confirming paper was published. Ask a question in plain language and the answer
is composed only from cited evidence, or it declines rather than invent. Demonstrated
end-to-end on antimicrobial resistance: Achilles names not the gene *associated* with
resistance but the **reversible target** resistance *creates* through collateral
sensitivity, folds it with AlphaFold, and proposes a cited antibiotic-cycling hypothesis —
a research hypothesis, never medical advice. The same pipeline is domain-agnostic: bring
your own data, or reproduce the entire graph offline from public sources (PubMLST, Europe
PMC, CARD, UniProt, ChEMBL). Deterministic core, provenance on every edge, reproducible
from public data, MIT.

## Reproduce from public data

```bash
make db            # Postgres + pgvector
make seed-public   # PubMLST lineage + committed public caches (no private data)
make backend       # FastAPI  :8000
make frontend      # Next.js  :3000
```

The deployed public database was seeded by exactly this path (70 strains, 490 variants,
12 genes, 61 edges / 44 grounded, 96 papers, 5 targets, 10 cited collateral-sensitivity
pairs). No BurkData or other private artifact is in the repo or the deployed image.

## Verified live (at submission)

- `GET /api/validation` → 9/9 recovered, 4/4 refused, **0 fabricated**, every claim cited
  to CARD + PMID.
- `GET /api/validation/redteam?gene=MarR&target=vancomycin` → **refused** (honest, no
  fabrication).
- `GET /api/ask` → grounded, cited answer with an LLM synthesis whose every sentence maps
  to a numbered claim; refuses when nothing is grounded.
- `GET /api/docking` → cited inhibitor (CCCP, PubChem 2603, CARD:ARO:3000074), **ready to
  dock** (no fabricated pose).
- Frontend at HEAD: blank/generic default, Demo-data toggle loads the AMR example, Ask +
  persona lenses + "bring your own data" all present.

## One honest note for the pitch

Cycling is framed everywhere as a **research hypothesis, not medical advice**. The docking
pose is not yet computed (no Tamarind key at submission) — the inhibitor is cited and shown
"ready to dock"; say that, don't imply a pose. Optionally run `make dock-targets` with a
Tamarind key to populate it before recording.
