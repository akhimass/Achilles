# Achilles — positioning against the AI-in-drug-development pipeline

**One line:** most AI target-ID names a gene *associated* with resistance; Achilles names
the vulnerability resistance *creates* — the reversible target — and grounds every claim
in real, cited evidence.

## Where we sit in the pipeline

Reference: Zhang K., Yang X., Wang Y., Yu Y., Huang N., Li G., Li X., Wu J.C. & Yang S.
*Artificial intelligence in drug development.* **Nature Medicine 31, 45–59 (2025)**
(Review, 20 Jan 2025) — Figure 1 lays out six stages, from **target identification**
through post-market surveillance, and the abstract closes by promising to "critically
examine the prevailing challenges."

Achilles lives in **Stage 1 — Target identification**. That stage's own AI applications,
per Figure 1, are: multi-omics analysis, biological-network construction, literature /
real-world mining, **knowledge-graph construction**, and **target validation**. Achilles
implements four of those five directly:

| Figure 1, Stage 1 application | In Achilles |
|---|---|
| Knowledge-graph construction | the `evidence_edges` graph is the product |
| Literature / real-world mining | Europe PMC → typed claims → grounded edges |
| Biological-network construction | strain → variant → gene → target → edge |
| Target validation | grounding vs CARD / UniProt / ChEMBL; ranked targets |

## The gap Stage 1 actually has (and what we claim)

The figure lists "target validation" as if it's solved. It isn't. The field generates
target candidates in abundance; almost none are **traceable, grounded, or reproducible**,
so they don't survive validation and biologists don't trust them. That is the
industrial-scale version of "a beautiful shell over an LLM." *(This is our reading of the
gap, argued from Figure 1 and the field — the paper's full challenges section is
subscription-gated; we don't quote claims we can't verify.)*

Two things Achilles does about it:

1. **Trust is built, not promised.** Provenance on every edge; grounded-vs-abstract-only
   tiers; an expandable per-edge trace that separates what was **computed**
   (deterministic) from what was **narrated** (LLM); downloadable receipts (JSON/CSV).
   - **Provenance coverage: 100%** — all **61** evidence edges carry a PMID and/or a
     CARD/UniProt/ChEMBL accession (validator-enforced). **72%** (44/61) are corroborated
     against a reference database; the rest are labelled *abstract-only*, never as
     validated. **96** papers indexed.
2. **A target-selection principle the figure doesn't have.** None of Stage 1's five
   applications encodes *which* target is worth acting on. Achilles adds one:
   **reversibility / collateral sensitivity** — target the vulnerability resistance
   creates. Its "what real evolution did next" beat is **retrieval over real evolved
   lineages, never prediction**.

## The honest boundary (say it before a judge does)

- Achilles grounds in *existing* evidence — a strength for trust, but it surfaces and
  ranks known-adjacent targets; it does not invent unknown biology from scratch. Say
  "evidence-grounded and traceable," never "validated to work."
- Scope is AMR (depth), not general Stage 1 (breadth).

## The 60-second demo

pick strain → a flipper gene lights up → fold it (AlphaFold, pLDDT) → grounded evidence
with a PMID + CARD chip → *what real lineages did next* (retrieved) → reciprocal-CS
cycling hypothesis, with its caveat. One path: novelty, rigor, payoff.

> Defensible one-liner: *Stage 1's biggest AI gap isn't finding more targets — it's
> finding trustworthy ones and knowing which are worth acting on. Achilles grounds every
> target to public provenance (trust) and ranks by reversibility (worth acting on).*

_If you drop the article PDF into the repo, I'll read the actual challenges section and
tighten these claims to its exact wording._
