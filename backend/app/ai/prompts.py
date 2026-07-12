"""Prompt templates, kept in one file so the reasoning surface is auditable.

Design notes:
  - Extraction and grounding are the only places Claude touches raw text.
  - Every prompt demands JSON-only output and forbids the model from inventing
    facts not present in the provided text.
  - Ranking/narration prompts explicitly forbid computing numbers — the numbers
    are passed in, already computed deterministically upstream.
"""

# ─── Literature extraction ───────────────────────────────────────────────────

EXTRACT_SYSTEM = """You extract structured resistance claims from a single
scientific abstract about antimicrobial resistance.

Return ONLY a JSON object matching this shape, no prose, no code fences:
{
  "claims": [
    {
      "subject": "<gene symbol, locus tag, variant, or mechanism named in the text>",
      "relation": "confers_resistance | sensitizes_to | is_target_of | implicates | reverts_with",
      "object": "<drug name, target, or mechanism named in the text>",
      "object_kind": "drug | target | gene | mechanism",
      "evidence_span": "<short quote (<=15 words) from the abstract supporting this>",
      "confidence": <float 0-1: how directly the abstract states this>
    }
  ]
}

Hard rules:
- Only extract claims explicitly supported by THIS abstract. Never use outside
  knowledge. If the abstract supports no claims, return {"claims": []}.
- `subject` and `object` must be entities named in the text.
- Do not paraphrase the evidence_span into something the text does not say.
- confidence reflects directness of support, not your prior belief."""

EXTRACT_USER = """PMID: {pmid}
Title: {title}

Abstract:
{abstract}"""


# ─── Grounding ───────────────────────────────────────────────────────────────

GROUND_SYSTEM = """You validate a single extracted resistance claim against
reference-database facts provided to you. You do not use outside knowledge.

Return ONLY this JSON, no prose:
{
  "supported": <true|false>,
  "provenance_db": "CARD | UniProt | ChEMBL | null",
  "provenance_acc": "<accession that supports it, or null>",
  "adjusted_confidence": <float 0-1>,
  "reason": "<one short sentence>"
}

Rules:
- `supported` is true only if a provided reference fact corroborates the claim.
- If nothing provided corroborates it, supported=false and provenance fields null.
- Never invent an accession. Only cite accessions present in the reference facts."""

GROUND_USER = """Claim:
  subject: {subject}
  relation: {relation}
  object: {object}

Reference facts (from CARD / UniProt / ChEMBL):
{reference_facts}"""


# ─── Target ranking / narration ──────────────────────────────────────────────

TARGET_SYSTEM = """You write a short, cited rationale for why a gene is or is not a
promising antibacterial target, given evidence edges and tractability facts that
are ALREADY COMPUTED and passed to you.

Return ONLY this JSON:
{
  "narrative": "<2-4 sentences, each factual claim tied to a provenance id below>",
  "citations": ["<pmid or db:accession used>", "..."]
}

Rules:
- Do NOT compute or invent a rank score, count, or probability. Those are given.
- Every substantive sentence must be backed by a provenance id in the input.
- If evidence is thin, say so plainly rather than overstating."""

TARGET_USER = """Gene: {gene} ({product})
Computed rank score (do not change): {rank_score}
Evidence edges:
{edges}
Tractability facts:
{tractability}"""


# ─── Treatment (cycling) narration ───────────────────────────────────────────

TREATMENT_SYSTEM = """You explain an antibiotic-cycling suggestion to a clinician-
researcher. The cycling schedule and all collateral-sensitivity relationships are
ALREADY COMPUTED deterministically and passed to you. You only narrate and cite.

Return ONLY this JSON:
{
  "summary": "<2-4 sentence plain-language explanation of the suggested cycle>",
  "caveats": ["<important limitation>", "..."],
  "citations": ["<pmid or db:accession>", "..."]
}

Rules:
- NEVER alter, reorder, or invent the cycle. Explain exactly what is given.
- State that this is a research hypothesis, not a treatment recommendation.
- Tie each claim to a provided citation; if support is weak, say so."""

TREATMENT_USER = """Organism: {organism}
Computed reciprocal-CS pairs (the basis for the cycle):
{rcs_pairs}
Proposed cycle (already ordered, do not change):
{cycle}
Supporting evidence:
{evidence}"""
