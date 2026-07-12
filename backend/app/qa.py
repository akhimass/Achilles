"""Grounded question-answering core — the anti-"AI-slop" ask surface.

A user (bench researcher, physician, or computational researcher) asks a question in
plain language. Instead of free-associating an answer, Achilles RETRIEVES grounded
evidence from its own graph and answers ONLY from that — every claim cited, and an
explicit REFUSAL when nothing grounded is found. The optional LLM step (ai/ask.py)
merely phrases the retrieved claims; it may not add a fact that isn't in them.

This module is the pure, deterministic core: intent detection, claim shaping from
retrieval results, the always-present deterministic summary, per-persona framing/
caveats, and the refusal rule. No LLM, no DB, no network — fully unit-testable.
"""

from __future__ import annotations

# Intent is used only to FRAME the grounded answer (lens + caveats + which viz), never
# to invent content. Order matters: earlier categories win on overlap.
_INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("treatment", ("treat", "cycle", "cycling", "regimen", "therapy", "antibiotic",
                   "sensiti", "collateral", "combination")),
    ("target", ("target", "druggable", "tractab", "inhibitor", "dock", "pocket")),
    ("provenance", ("cite", "citation", "source", "provenance", "reproduc", "validat",
                    "confidence", "grounded")),
    ("mechanism", ("mechanism", "resist", "efflux", "pump", "mutation", "confers",
                   "regulat", "operon")),
]

PERSONAS = ("researcher", "physician", "computational")


def detect_intent(question: str) -> str:
    """Classify the question's lens deterministically. Falls back to 'general'."""
    q = (question or "").lower()
    for intent, keys in _INTENT_KEYWORDS:
        if any(k in q for k in keys):
            return intent
    return "general"


def normalize_persona(persona: str | None) -> str:
    p = (persona or "").strip().lower()
    return p if p in PERSONAS else "researcher"


def _claim_from_result(r: dict) -> dict:
    """Shape one ranked retrieval result into a cited claim card. Pure."""
    extra = r.get("extra") or {}
    return {
        "kind": r.get("kind"),
        "title": r.get("title"),
        "snippet": r.get("snippet"),
        "relation": extra.get("relation"),
        "gene_locus": extra.get("gene_locus") or extra.get("locus_tag"),
        "confidence": extra.get("confidence"),
        "grounded": bool(r.get("grounded")),
        "score": r.get("score"),
        "provenance": r.get("provenance") or {},
    }


def _persona_caveats(persona: str, intent: str) -> list[str]:
    caveats: list[str] = []
    if persona == "physician" or intent == "treatment":
        caveats.append(
            "Any treatment framing here is a research hypothesis from in-vitro evidence — "
            "not a treatment recommendation; no dosing, PK, or in-vivo validation is modeled."
        )
    if persona == "computational":
        caveats.append(
            "Every claim below links to a PMID or reference-DB accession, with its extraction "
            "confidence — nothing is asserted without provenance."
        )
    return caveats


def _deterministic_summary(claims: list[dict], intent: str, refused: bool) -> str:
    """A factual, no-LLM one-liner that is ALWAYS present (even without a model)."""
    if refused:
        return (
            "No grounded evidence in the graph answers this, so the engine refuses rather "
            "than fabricate one. Try a gene (MarR, AraC/MarA, efflux) or a topic "
            "(efflux, ciprofloxacin, tigecycline, collateral sensitivity)."
        )
    n = len(claims)
    grounded_ct = sum(1 for c in claims if c["grounded"])
    lens = {
        "treatment": "bearing on treatment",
        "target": "bearing on target tractability",
        "provenance": "with their provenance",
        "mechanism": "on the mechanism",
        "general": "",
    }.get(intent, "")
    tail = f" {lens}" if lens else ""
    return (
        f"{n} grounded claim{'' if n == 1 else 's'}{tail} were retrieved from the graph "
        f"({grounded_ct} reference-corroborated) — each cited below. Any synthesis is "
        "composed only from these; nothing outside the graph is added."
    )


def build_answer(
    question: str, persona: str, results: list[dict], *, max_claims: int = 8
) -> dict:
    """Assemble the grounded answer packet from ranked retrieval results. Pure.

    Only GROUNDED results become claims (the anti-slop rule); if there are none, the
    packet is a refusal. The LLM synthesis (added by the router when enabled) can only
    ever phrase these claims.
    """
    persona = normalize_persona(persona)
    intent = detect_intent(question)
    grounded = [r for r in results if r.get("grounded")]
    claims = [_claim_from_result(r) for r in grounded[:max_claims]]
    refused = len(claims) == 0

    return {
        "question": question,
        "persona": persona,
        "intent": intent,
        "grounded": not refused,
        "refused": refused,
        "claims": claims,
        "deterministic_summary": _deterministic_summary(claims, intent, refused),
        "caveats": _persona_caveats(persona, intent),
        "answer": None,  # optional LLM synthesis, filled in by the router when enabled
        "counts": {
            "claims": len(claims),
            "grounded": sum(1 for c in claims if c["grounded"]),
            "retrieved": len(results),
        },
    }


def citation_label(prov: dict) -> str | None:
    """Human/citation id for a claim's provenance: PMID or DB:ACC."""
    if not prov:
        return None
    if prov.get("pmid"):
        return f"PMID {prov['pmid']}"
    if prov.get("db") and prov.get("acc"):
        return f"{prov['db']}:{prov['acc']}"
    return None
