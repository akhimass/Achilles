# Demo kit — which files power which beat, and what to record

**Read this first.** There are two datasets. Pick the right one before you record.

| Mode | Seed | Data | Safe to publish? |
|---|---|---|---|
| **A — public (recommended)** | live site, or `make seed-public` | files **1–8** below (all public) | ✅ Yes. This is what `DEMO_SCRIPT.md` is written for. |
| **B — local-rich** | `make seed` with file **9** present | adds BurkData (real experimental evolution) | ⛔ **No** — file 9 is private (Dr. Sung's unpublished lab data). Local exploration only, or a private session with his clearance. **Do not post a video that shows it.** |

The **live deployment (`achilles-science.vercel.app`) is Mode A** — it is seeded from the
public path and contains **no BurkData**. Record there and every frame is public and safe.

---

## Numbered file manifest

### Public — shipped, on the live site (Mode A)

1. **`data/demo/bmultivorans_pubmlst.json`** — real public PubMLST lineage (70 isolates,
   7-locus MLST). *Powers:* the **Lineage** tree; the BYO panel's **"Try an example"**.
2. **`data/demo/literature/corpus.json`** — the grounded evidence graph (96 PubMed papers,
   61 edges / 44 grounded, with years). *Powers:* **Evidence**, **Ask**, **Targets**,
   **Validation**, **Retrodiction**, **Bridge**. The backbone of almost every beat.
3. **`data/demo/benchmark/known_relationships.json`** — the **29 controls** (12 positives +
   17 adversarial negatives). *Powers:* **Prove-it / Validation**, **Red-team**, the
   **audit ledger**, and the **downloadable report**.
4. **`data/demo/collateral/public_cs.json`** — 5 cited reciprocal collateral-sensitivity
   pairs (PMID 32335276). *Powers:* **Cycling** and the **Bridge** treatment side.
5. **`data/demo/docking/ligands.json`** — the cited efflux inhibitor CCCP
   (PubChem 2603, CARD:ARO:3000074). *Powers:* the **docking** beat ("ready to dock").
6. **`data/demo/structures/WP_006410546.1.json`** — the MarR AlphaFold fold (pLDDT 88),
   via Tamarind. *Powers:* the **Structure** viewer.
7. **`data/demo/reference/`** — reference gene + ChEMBL tractability caches. *Powers:* the
   **tractability** signal on ranked **Targets**.
8. **`data/demo/narration/`** — pre-reviewed, cached LLM narration (cycle / target /
   trajectory). *Powers:* the opt-in narrated summaries; the demo works without it.

### Private — BurkData, local only (Mode B — do NOT publish)

9. **`data/demo/bmultivorans_burkdata.json`** — **PRIVATE.** Dr. Sung's real
   experimental-evolution record: 47 isolates, 11 lineages, per-gene indel flippers, and
   per-lineage resistance/sensitivity. *Powers (locally only):* a richer **Lineage** tree,
   the **"What real evolution did next"** (trajectory) beat, and BurkData-derived cycling.
   **Git-ignored, never committed, never on the live site.** If you record with this
   loaded, do not submit that video.

---

## Per-beat → what it uses (Mode A / public)

Follow `DEMO_SCRIPT.md`. Every beat runs against the **live public API** — no files to load
by hand.

1. **Open blank / toggle demo** → seeded public graph (files 1–2).
2. **Prove it** → `/api/validation`, `/api/audit`, `/api/report/validation` (files 3 + 2).
3. **Red-team** → `/api/validation/redteam` (files 3 + 2).
4. **Retrodiction** → `/api/validation/retrodiction` (file 2, the paper years).
5. **Ask** → `/api/ask` (file 2).
6. **Target → structure → inhibitor** → `/api/targets`, `/api/structure`, `/api/docking`
   (files 2, 6, 5, 7).
7. **Bridge** → `/api/bridge` (files 2 + 4).
8. **Generalize / BYO** → `/api/ingest/example` — "Try an example" is file 1
   (real Burkholderia); "Try another organism" is an illustrative, in-code cohort.
9. **MCP closer** → Claude Code / Cowork calling the live API (all public), or the `/mcp`
   page.

## The one honest line

Record Mode A. It shows the full pipeline — lineage, prove-it, red-team, retrodiction, ask,
targets, structure, docking, bridge, MCP — on **public data only**. BurkData makes the local
trajectory/cycling beats richer, but it is private and must not appear in a submitted video.
