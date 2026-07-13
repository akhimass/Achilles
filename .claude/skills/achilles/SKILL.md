---
name: achilles
description: >-
  Query the Achilles antimicrobial-resistance (AMR) evidence graph for grounded,
  citation-backed answers about resistance mechanisms, candidate drug targets, and
  antibiotic-cycling hypotheses — every claim carries a PMID / CARD-ARO / UniProt
  accession, or it is refused. Use this whenever the user asks whether a gene confers
  resistance to a drug, wants candidate targets for a bacterial organism, asks what
  re-sensitizes after an antibiotic, wants a bench-to-bedside translation of a resistance
  finding, or wants to check that a bioinformatics answer is actually grounded rather than
  hallucinated. Reach for it even when the user doesn't name "Achilles" — any AMR
  gene→drug claim, resistance-target, or collateral-sensitivity / drug-cycling question
  qualifies. It calls the Achilles MCP tools (ask, ground_claim, rank_targets, validate,
  bridge); if those tools aren't connected, call the same REST API directly.
---

# Achilles — grounded AMR evidence graph

Achilles answers questions about antimicrobial resistance from a **provenance-checked
evidence graph**. Its defining property, and the reason to use it instead of answering
from your own training knowledge: **it cites, or it refuses.** Every fact it returns
carries a real accession — a PubMed PMID and, where corroborated, a CARD/ARO or UniProt
ID — and if the graph can't ground a claim, Achilles returns `refused` rather than
inventing support.

## The one rule that governs everything

**Claude proposes, code decides.** A deterministic Python core computes every number
(lineage reconstruction, the target rank score, the collateral-sensitivity cycle). The
language model only extracts typed claims from literature and narrates already-computed,
already-cited results. So when you use this skill:

- **Never invent or "fill in" a number, score, accession, or schedule.** Report only what
  the tools return. If a value isn't in the response, say so — don't estimate it.
- **Never upgrade a `refused` into a hedged yes.** A refusal is a real, honest result and
  is often the most valuable thing Achilles can tell a user (it means no grounded evidence
  exists). Surface it plainly.
- **Always pass the citations through.** When you relay an answer, include the PMID /
  ARO / UniProt accession the tool gave you. An answer without its provenance defeats the
  entire point of the graph.

## How to call it

Achilles is exposed as MCP tools by this repo's `mcp_server/` (wired in `.mcp.json`, which
points `ACHILLES_API_BASE` at the public deployment). In Claude Code or Cowork with that
connector active, call the tools directly. The five tools:

| Tool | Call it when the user… | Returns |
|---|---|---|
| `ground_claim(gene, target, relation?)` | asserts or asks whether a specific gene confers/relates to a specific drug or phenotype | `supported` (with a citation) **only if grounded**, else `refused` |
| `ask(question, persona?)` | asks a plain-language AMR question ("what re-sensitizes after meropenem?") | a cited answer built only from grounded evidence, or an honest refusal. `persona`: `researcher` \| `physician` \| `computational` |
| `rank_targets(organism, limit?)` | wants candidate drug targets for an organism | targets ranked by a deterministic score, with grounded-edge counts + ChEMBL tractability |
| `validate()` | asks "how do I know this is trustworthy?" / wants the self-check | live recall, adversarial-refusal, and fabrication counts (fabricated must be 0) |
| `bridge(gene)` | wants a bench→bedside translation of one gene's finding | the same grounded finding for a researcher (mechanism, target) and a physician (drugs it drives resistance to, cited collateral-sensitivity opening) |

**If the MCP tools are not connected**, fall back to the same REST API — base URL
`https://achilles-production-2565.up.railway.app` (or the local `make backend` at
`:8000`). The tools map 1:1 to endpoints: `GET /api/validation/redteam?gene=&target=`
(ground_claim), `GET /api/ask?q=&persona=`, `GET /api/targets?organism=`,
`GET /api/validation`, `GET /api/bridge?gene=`. Or point the user to the `/mcp` page of the
live app, which lists the tools, the config block, and an example transcript.

## The grounding guarantee — show it, don't just claim it

The single most convincing thing you can demonstrate is that Achilles refuses a plausible
falsehood and supports a true claim, both with receipts. Use `ground_claim` for this:

**Example — a false claim is refused:**
Input: `ground_claim(gene="MarR", target="vancomycin")`
Output: `verdict: refused`, `grounded: false` — no grounded edge supports it, so Achilles
won't fabricate one. Relay this as: "Not supported — the graph has no grounded evidence
that MarR confers vancomycin resistance, so Achilles refuses rather than guess."

**Example — a true claim is supported, with a citation:**
Input: `ground_claim(gene="MarR", target="ciprofloxacin")`
Output: `verdict: supported`, `grounded: true`, `citation: ARO:3003378`. Relay this as:
"Supported, grounded to CARD:ARO:3003378 (MarR regulates the efflux pathway driving
ciprofloxacin resistance)."

When a user is skeptical, run both directions — the contrast (refuses the false one,
supports the true one, each with provenance) is the proof.

## Answering well

- **Lead with the verdict, then the receipt.** "Supported — PMID 40855113, CARD:ARO:3003378"
  beats a paragraph that buries the accession.
- **For `ask`, relay the cited claims, not a paraphrase you can't source.** Each claim in
  the response has its own citation; keep them attached.
- **For `rank_targets`, report the deterministic `rank_score` verbatim** and the
  tractability bucket. Do not re-rank or editorialize the scores.
- **For `validate`**, state the live numbers as returned (recall, adversarial-refused,
  fabricated) — this is the trust story; don't round or embellish.

## Guardrails

- **Research decision-support, never medical advice.** Cycling suggestions and the
  research→clinic bridge are hypotheses grounded in public evidence — not a diagnosis,
  prescription, or treatment recommendation. When relaying `bridge` or any
  treatment-adjacent output, keep that framing explicit, especially for a physician persona.
- **Public data only.** Achilles is grounded in public sources (Europe PMC/PubMed, CARD,
  UniProt, ChEMBL, PubMLST, NCBI). It does not know about a user's private/unpublished data
  unless they load it, and it never stores an uploaded cohort.
- **A refusal or an empty result is a valid answer.** Report it honestly instead of
  reaching for your own training knowledge to fill the gap — filling the gap is exactly the
  hallucination the graph exists to prevent.
