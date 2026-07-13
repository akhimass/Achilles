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
deterministic core does the math; the model only reads, retrieves, and cites. Its edge is
verifiability you can break on stage. Against **29 independent public controls** it recovers
known biology (**12/12**), refuses an adversarial battery of plausible falsehoods
(**17/17**), and fabricates nothing (**0**) — and writes the result to a **tamper-evident,
hash-chained ledger** anyone can re-verify. On a time-split hold-out it goes further,
**anticipating** relationships before the confirming paper was published. Ask a question in
plain language and the answer is built only from cited evidence, or it declines. Shown
end-to-end on antimicrobial resistance: it names not the gene *associated* with resistance
but the **reversible target** resistance *creates*, folds it with AlphaFold, proposes a
cited cycling hypothesis, and **bridges bench to bedside** — the same grounded finding,
clinician-framed, never medical advice. The pipeline is domain-agnostic and reproducible
offline from public data. Deterministic core, provenance on every edge, MIT.

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

- `GET /api/validation` → **12/12 recovered · 17/17 adversarial refused · 0 fabricated**
  (29 public controls), every claim cited to CARD + PMID.
- `GET /api/audit` → the prove-it result as a **sha256 hash-chained ledger** (head
  fingerprint + per-entry chain); `POST /api/audit/verify` re-checks the chain — tamper-
  evident and reproducible.
- `GET /api/validation/redteam?gene=MarR&target=vancomycin` → **refused** (honest, no
  fabrication).
- `GET /api/bridge` → one grounded finding translated **researcher → physician** (same
  citations, clinician framing, flagged research-not-advice); mirrored in-console in the
  Treatment chapter, tied to the selected gene.
- `GET /api/ask` → grounded, cited answer with an LLM synthesis whose every sentence maps
  to a numbered claim; refuses when nothing is grounded.
- `GET /api/docking` → cited inhibitor (CCCP, PubChem 2603, CARD:ARO:3000074), **ready to
  dock** (no fabricated pose).
- `GET /api/report/validation` → a downloadable, self-contained **HTML audit report** (head
  fingerprint + cited-control table + embedded ledger + `curl` re-verify instructions). The
  Validation panel offers "Download audit report (HTML)" and "ledger (JSON, re-verifiable)".
- `/mcp` (+ `mcp_server/`, `.mcp.json`) → Achilles as **tools any Claude agent calls** in
  Claude Code / Cowork (`ask`, `ground_claim`, `rank_targets`, `validate`, `bridge`) — it
  cites, or it refuses. The showcase page has the tool set, config, and an example transcript.
- `/methods` (+ `METHODS.md`) — deterministic core, grounding, validation@29, retrodiction,
  limitations, reproducibility.
- Frontend at HEAD: blank/generic default, Demo-data toggle loads the AMR example, Ask +
  persona lenses + "bring your own data" + the in-console research→clinic bridge, plus the
  `/mcp` showcase and the downloadable audit report.

## One honest note for the pitch

Cycling is framed everywhere as a **research hypothesis, not medical advice**. The docking
pose is not yet computed (no Tamarind key at submission) — the inhibitor is cited and shown
"ready to dock"; say that, don't imply a pose. Optionally run `make dock-targets` with a
Tamarind key to populate it before recording.
