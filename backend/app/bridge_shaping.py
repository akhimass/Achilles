"""The bridge — one grounded finding, translated bench → bedside.

Researchers and physicians read the same resistance biology through different lenses. The
bridge takes a SINGLE gene's GROUNDED evidence and composes two views of it — the
researcher's target-identification view (mechanism, tractable target, structure) and the
physician's treatment view (what resistance it drives, the collateral-sensitivity opening,
a cited cycling hypothesis) — carrying the SAME provenance across the handoff. Nothing is
generated: every claim is an already-grounded edge or a deterministically-computed,
literature-cited cycle. Pure and unit-testable; the router supplies the data.
"""

from __future__ import annotations

_RESIST = "confers_resistance"
_MECH = ("implicates", "is_target_of", "sensitizes_to")

# Always attached to the clinical view — a translation is never a prescription.
_CLINICAL_CAVEATS = [
    "Research evidence translated for interpretation — NOT a treatment recommendation, "
    "diagnosis, or dosing guidance.",
    "Any cycling strategy is an in-vitro / literature hypothesis; collateral sensitivity is "
    "frequently non-reciprocal and strain-specific, and no PK, toxicity, or in-vivo "
    "validation is modeled.",
]


def _clean(text: str | None) -> str:
    return (text or "").strip()


def _dedup(seq: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for s in seq:
        k = s.lower()
        if s and k not in seen:
            seen[k] = s  # preserve original casing
    return list(seen.values())


def _citation(prov: dict | None) -> dict | None:
    if not prov:
        return None
    if prov.get("pmid"):
        return {"label": f"PMID {prov['pmid']}", "url": prov.get("pubmed_url")}
    if prov.get("db") and prov.get("acc"):
        return {"label": f"{prov['db']}:{prov['acc']}", "url": prov.get("ref_url")}
    return None


def shape_bridge(
    gene: dict,
    grounded_edges: list[dict],
    target: dict | None = None,
    cycle: dict | None = None,
    organism: str = "",
) -> dict:
    """Compose the researcher→physician translation for one gene. Pure.

    grounded_edges: [{relation, target, provenance{pmid,pubmed_url,db,acc,ref_url}}] — the
    gene's GROUNDED edges only. target: ranked-target view or None. cycle: a shaped cycle
    payload (already cited) or None.
    """
    name = _clean(gene.get("name")) or _clean(gene.get("locus"))
    product = _clean(gene.get("product"))

    resistance_drugs = _dedup([
        _clean(e.get("target")) for e in grounded_edges if e.get("relation") == _RESIST
    ])
    mechanisms = _dedup([
        _clean(e.get("target")) for e in grounded_edges if e.get("relation") in _MECH
    ])

    claims = []
    for e in grounded_edges:
        cit = _citation(e.get("provenance"))
        if not cit:
            continue
        claims.append({
            "relation": e.get("relation"),
            "target": _clean(e.get("target")),
            "citation": cit,
        })

    # ── Researcher lens: target identification ──────────────────────────────
    research = {
        "lens": "Target identification",
        "gene": {"locus": gene.get("locus"), "name": name, "product": product},
        "mechanism": mechanisms[:4],
        "summary": (
            f"{name} — {product}. Grounded evidence implicates it in "
            + (", ".join(mechanisms[:3]) if mechanisms else "resistance biology")
            + "."
        ),
        "target": target,  # rank_score / tractability / structure_available / counts, or None
        "grounded_claims": claims[:6],
    }

    # ── Physician lens: treatment optimization (translated) ─────────────────
    opening = None
    cited_cycle = None
    if cycle and cycle.get("cycle"):
        cited_cycle = {
            "cycle": cycle.get("cycle", []),
            "summary": cycle.get("summary"),
        }
        for p in cycle.get("rcs_pairs", []):
            prov = p.get("provenance")
            if prov and prov.get("pmid"):
                opening = {
                    "drug_a": p.get("drug_a"), "drug_b": p.get("drug_b"),
                    "citation": {"label": f"PMID {prov['pmid']}", "url": prov.get("pubmed_url")},
                }
                break

    clinic = {
        "lens": "Treatment optimization",
        "drives_resistance_to": resistance_drugs,
        "collateral_opening": opening,
        "cited_cycle": cited_cycle,
        "actionable": _actionable(name, resistance_drugs, cited_cycle, opening, organism),
        "caveats": list(_CLINICAL_CAVEATS),
    }

    n_cited = len(claims) + (1 if opening else 0)
    return {
        "organism": organism,
        "gene": research["gene"],
        "research": research,
        "clinic": clinic,
        "handoff": (
            f"The same grounded finding, translated: {name}"
            + (f" drives resistance to {', '.join(resistance_drugs[:3])}" if resistance_drugs else "")
            + (" and opens a collateral-sensitivity strategy" if cited_cycle else "")
            + " — provenance carried from target identification to the bedside."
        ),
        "provenance_carried": n_cited,
    }


def _actionable(
    name: str, drugs: list[str], cited_cycle: dict | None, opening: dict | None, organism: str
) -> str:
    if not drugs and not cited_cycle:
        return (
            f"No grounded resistance-to-drug or collateral-sensitivity translation is "
            f"available for {name} yet — the engine states that rather than guess."
        )
    parts: list[str] = []
    if drugs:
        parts.append(
            f"An isolate whose resistance runs through {name} is expected to resist "
            f"{', '.join(drugs[:3])} (each cited)."
        )
    if opening:
        parts.append(
            f"The reciprocal collateral-sensitivity opening reported for {organism} is "
            f"{opening['drug_a']} ⇄ {opening['drug_b']} ({opening['citation']['label']}); "
            "alternating reciprocally-sensitizing drugs is hypothesized to keep resistance "
            "from fixing."
        )
    elif cited_cycle:
        parts.append(
            "A cited collateral-sensitivity cycling strategy is available for this organism "
            "(see the cycle)."
        )
    return " ".join(parts)
