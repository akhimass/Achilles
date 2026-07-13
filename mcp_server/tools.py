"""Achilles MCP tools — the grounded evidence graph as callable primitives.

Each tool calls the live Achilles API (ACHILLES_API_BASE) and returns a compact,
CITED result for a Claude agent (Claude Code / Cowork) to use. The response→text
shaping is pure and unit-tested; the network call is a thin wrapper. Nothing here
fabricates: an ungrounded claim comes back `refused`, and every fact carries a citation.
"""

from __future__ import annotations

import os

import httpx

API_BASE = os.getenv(
    "ACHILLES_API_BASE", "https://achilles-production-2565.up.railway.app"
).rstrip("/")


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=45) as c:
        r = await c.get(f"{API_BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


# ─── Pure shapers (unit-tested) ──────────────────────────────────────────────

def shape_ask(d: dict) -> dict:
    if d.get("refused"):
        return {"grounded": False, "answer": d.get("deterministic_summary"), "claims": []}
    ans = d.get("answer")
    summary = ans.get("summary") if ans else d.get("deterministic_summary")
    claims = [
        {"claim": c.get("title"), "cite": c.get("citation")}
        for c in d.get("claims", [])
        if c.get("citation")
    ]
    return {
        "grounded": True,
        "answer": summary,
        "claims": claims[:6],
        "caveats": d.get("caveats", []),
        "source": "llm" if ans else "retrieval",
    }


def shape_redteam(d: dict) -> dict:
    prov = d.get("provenance") or {}
    return {
        "verdict": d.get("verdict"),  # supported | weak | refused | unknown_gene
        "grounded": d.get("grounded"),
        "reason": d.get("reason"),
        "citation": prov.get("acc") or prov.get("pmid"),
    }


def shape_targets(d: dict, limit: int = 5) -> list[dict]:
    ts = sorted(d.get("targets", []), key=lambda t: (t.get("rank_score") or 0), reverse=True)
    out = []
    for t in ts[:limit]:
        tract = t.get("tractability") or {}
        out.append({
            "gene": t.get("name") or t.get("locus_tag"),
            "locus": t.get("locus_tag"),
            "rank_score": t.get("rank_score"),
            "grounded_edges": (t.get("evidence_counts") or {}).get("grounded"),
            "tractability": tract.get("bucket") if isinstance(tract, dict) else None,
        })
    return out


def shape_validation(d: dict) -> dict:
    m = d.get("metrics", {})
    return {
        "recovered": f"{m.get('recovered')}/{m.get('positives')}",
        "adversarial_refused": f"{m.get('refused')}/{m.get('negatives')}",
        "fabricated": m.get("fabricated"),
        "controls": (m.get("positives") or 0) + (m.get("negatives") or 0),
        "clean": m.get("clean"),
    }


def shape_bridge(d: dict) -> dict:
    if not d.get("found"):
        return {"found": False, "reason": d.get("reason")}
    research = d.get("research") or {}
    clinic = d.get("clinic") or {}
    return {
        "found": True,
        "gene": (d.get("gene") or {}).get("name"),
        "mechanism": research.get("mechanism"),
        "drives_resistance_to": clinic.get("drives_resistance_to"),
        "cited_cycle": (clinic.get("cited_cycle") or {}).get("cycle"),
        "handoff": d.get("handoff"),
        "caveats": clinic.get("caveats"),
    }


# ─── Async tools (called by the MCP server) ──────────────────────────────────

async def ask(question: str, persona: str = "researcher") -> dict:
    """Ask the grounded graph a question. Cited answer, or an honest refusal."""
    return shape_ask(await _get(
        "/api/ask", {"q": question, "persona": persona, "narrate": "true"}
    ))


async def ground_claim(gene: str, target: str, relation: str | None = None) -> dict:
    """Adjudicate a claim (e.g. gene='MarR', target='ciprofloxacin') against grounded
    evidence — 'supported' with a citation only if the graph backs it, else 'refused'."""
    params = {"gene": gene, "target": target}
    if relation:
        params["relation"] = relation
    return shape_redteam(await _get("/api/validation/redteam", params))


async def rank_targets(organism: str = "Burkholderia multivorans", limit: int = 5) -> list[dict]:
    """Top candidate targets for an organism, by deterministic rank score, with tractability."""
    return shape_targets(await _get("/api/targets", {"organism": organism}), limit)


async def validate() -> dict:
    """The self-validation result: recall, adversarial refusal, and fabrication count."""
    return shape_validation(await _get("/api/validation"))


async def bridge(gene: str) -> dict:
    """Translate one gene's grounded finding researcher → physician (cited; not medical advice)."""
    return shape_bridge(await _get("/api/bridge", {"gene": gene}))
