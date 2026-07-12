"""Self-validation engine — the "prove-it" property that beats a search box.

Runs the *grounded* evidence graph against an independent set of public ground-truth
controls (data/demo/benchmark/known_relationships.json):

  - POSITIVE controls are established, publicly-cited resistance relationships. The
    engine should RECOVER each from a grounded edge (with its citation).
  - NEGATIVE controls are mechanistically false / unsupported. The engine should REFUSE
    each (no grounded edge). Any grounded support for a negative is a *fabrication* —
    the count that must be zero.

This is a deterministic, network-free, LLM-free check: same graph → same report. It
demonstrates two things a retrieval tool cannot claim by construction — that the
pipeline recovers known biology, and that it does not invent what isn't grounded.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.domain import ValidationItem, ValidationReport

BENCHMARK = (
    Path(__file__).resolve().parents[3] / "data" / "demo" / "benchmark" / "known_relationships.json"
)


def load_benchmark() -> dict:
    return json.loads(BENCHMARK.read_text())


# ─── Red-team: adjudicate a claim a judge types in, live ─────────────────────

# Public gene aliases → locus, so a judge can type "MarR" not a locus tag.
_GENE_ALIASES = {
    "marr": "A8H40_RS07590",
    "arac": "A8H40_RS24275", "mara": "A8H40_RS24275", "aracmara": "A8H40_RS24275",
    "lysr": "A8H40_RS17945",
    "efflux": "A8H40_RS19975", "dmt": "A8H40_RS19975", "effluxdmt": "A8H40_RS19975",
    "responseregulator": "A8H40_RS00780", "responsereg": "A8H40_RS00780",
}


def resolve_locus(gene: str | None) -> str | None:
    """Map a judge's gene input (name or locus tag) to a locus, or None."""
    if not gene:
        return None
    g = gene.strip()
    if g.upper().startswith("A8H40_"):
        return g.upper()
    key = "".join(c for c in g.lower() if c.isalnum())
    return _GENE_ALIASES.get(key)


def adjudicate(gene: str | None, target: str | None, edges: list[dict], relation: str | None = None) -> dict:
    """Judge a free-typed claim against the grounded graph. Pure, deterministic.

    Returns a verdict: ``supported`` (a grounded edge backs it, with citation),
    ``weak`` (only an abstract-only mention — not corroborated), ``refused`` (no
    evidence — the engine will not assert it), or ``unknown_gene``. The claim is never
    accepted on faith; it must match real grounded evidence to be supported.
    """
    locus = resolve_locus(gene)
    claim = {"gene": gene, "locus": locus, "relation": relation, "target": target}
    if not locus:
        return {"claim": claim, "verdict": "unknown_gene", "grounded": False,
                "reason": f"'{gene}' is not a gene in the demo graph. Try MarR, AraC/MarA, "
                          "LysR, efflux, or a locus tag."}
    term = (target or "").strip().lower()
    grounded_hit = abstract_hit = None
    for e in edges:
        if e.get("locus") != locus:
            continue
        if relation and e.get("relation") != relation:
            continue
        if term and term not in (e.get("target") or "").lower():
            continue
        if e.get("grounded"):
            grounded_hit = grounded_hit or e
        else:
            abstract_hit = abstract_hit or e

    if grounded_hit:
        return {"claim": claim, "verdict": "supported", "grounded": True,
                "matched_target": grounded_hit.get("target"),
                "matched_relation": grounded_hit.get("relation"),
                "provenance": grounded_hit.get("provenance") or {},
                "reason": "A grounded evidence edge in the graph supports this claim."}
    if abstract_hit:
        return {"claim": claim, "verdict": "weak", "grounded": False,
                "matched_target": abstract_hit.get("target"),
                "matched_relation": abstract_hit.get("relation"),
                "provenance": abstract_hit.get("provenance") or {},
                "reason": "Only an abstract-only mention exists — not corroborated against a "
                          "reference DB, so it is not asserted as validated."}
    return {"claim": claim, "verdict": "refused", "grounded": False, "provenance": {},
            "reason": "No grounded evidence in the graph supports this claim, so the engine "
                      "refuses it rather than fabricate support."}


# ─── Retrodiction: time-split foresight, not just recall ─────────────────────
#
# A search box can only tell you what a paper already says. The stronger claim is
# FORESIGHT: freeze the evidence at a cutoff year, hide everything published after it,
# and ask whether the pre-cutoff graph already pointed at a relationship that a LATER
# paper went on to confirm. This is a held-out test in TIME — harder than cross-lab
# generalization, and impossible for a retrieval tool to fake.
#
# Deterministic and honest: it separates "already grounded before the cutoff" (not a
# win) from "anticipated" (pre-cutoff signal pointed here) from "not anticipable" (we
# could NOT have called it — no pre-cutoff signal). Anticipation is graded: drug-level
# (a pre-cutoff edge named the same drug) is stronger than mechanism-level (the gene was
# already grounded as a resistance/efflux driver). Negatives are run too: a false claim
# must never be "anticipated" — foresight without fabrication.

# Relations that mean "this gene drives resistance" — the mechanism-level signal.
_RESISTANCE_RELATIONS = {"confers_resistance", "implicates", "is_target_of", "sensitizes_to"}


def _edge_year(edge: dict) -> int | None:
    y = edge.get("year")
    try:
        return int(y) if y is not None else None
    except (TypeError, ValueError):
        return None


def _term_hit(control: dict, edge: dict) -> bool:
    """Does this edge's target text mention any of the control's target terms?"""
    terms = [t.lower() for t in control.get("target_terms", [])]
    target = (edge.get("target") or "").lower()
    return bool(terms) and any(term in target for term in terms)


def _control_matches(control: dict, edge: dict) -> bool:
    """Same locus + relation + a target-term hit (the confirmation match)."""
    return (
        edge.get("locus") == control["locus"]
        and edge.get("relation") == control["relation"]
        and _term_hit(control, edge)
    )


def _retrodict_one(control: dict, edges: list[dict], cutoff: int) -> dict:
    """Classify one control under a time cutoff. Pure.

    Statuses:
      known_by_cutoff       — a grounded confirming edge already exists at/<= cutoff.
      anticipated_drug      — confirmation is post-cutoff, but a pre-cutoff edge named
                              the same drug/target (specific foresight).
      anticipated_mechanism — confirmation is post-cutoff; no drug-specific pre-cutoff
                              hit, but the gene was already grounded as a resistance/
                              efflux driver pre-cutoff (mechanism-level foresight).
      not_anticipable       — confirmation is post-cutoff and there is NO pre-cutoff
                              signal — an honest miss, not a fabricated call.
      unconfirmed           — no grounded confirming edge exists at any date.
    """
    grounded_conf = [
        e for e in edges if _control_matches(control, e) and e.get("grounded")
    ]
    if not grounded_conf:
        return {"status": "unconfirmed", "confirm_year": None,
                "pre_cutoff_signal": [], "confirming_edge": None}

    def _y(e: dict) -> int:
        return _edge_year(e) if _edge_year(e) is not None else 0

    earliest = min(grounded_conf, key=_y)
    confirm_year = _edge_year(earliest)

    # Grounded confirmation known at/<= cutoff → not a retrodiction win.
    if any((_edge_year(e) or 0) <= cutoff for e in grounded_conf):
        return {"status": "known_by_cutoff", "confirm_year": confirm_year,
                "pre_cutoff_signal": [], "confirming_edge": earliest}

    # Held out: confirmation is strictly post-cutoff. Look for pre-cutoff signal.
    locus = control["locus"]
    drug_sig = [
        e for e in edges
        if e.get("locus") == locus
        and (_edge_year(e) is not None and _edge_year(e) <= cutoff)
        and _term_hit(control, e)
    ]
    mech_sig = [
        e for e in edges
        if e.get("locus") == locus
        and e.get("grounded")
        and (_edge_year(e) is not None and _edge_year(e) <= cutoff)
        and e.get("relation") in _RESISTANCE_RELATIONS
    ]
    if drug_sig:
        status, signal = "anticipated_drug", drug_sig
    elif mech_sig:
        status, signal = "anticipated_mechanism", mech_sig
    else:
        status, signal = "not_anticipable", []
    return {"status": status, "confirm_year": confirm_year,
            "pre_cutoff_signal": signal[:4], "confirming_edge": earliest}


def retrodict(benchmark: dict, edges: list[dict], cutoff: int) -> dict:
    """Time-split foresight report over the grounded graph. Pure and deterministic.

    Freezes evidence at ``cutoff`` and measures how many later-confirmed relationships
    the pre-cutoff graph already pointed at — while proving no FALSE claim is ever
    "anticipated" (foresight without fabrication).
    """
    positives = []
    for c in benchmark.get("positives", []):
        r = _retrodict_one(c, edges, cutoff)
        positives.append({
            "gene": c.get("gene", c["locus"]), "locus": c["locus"],
            "relation": c["relation"], "target_terms": c.get("target_terms", []),
            "citation": c.get("citation"), "note": c.get("note"),
            **r,
            "confirming_edge": _slim(r.get("confirming_edge")),
            "pre_cutoff_signal": [_slim(e) for e in r.get("pre_cutoff_signal", [])],
        })

    # Precision under time-split: a false control must never be "anticipated".
    false_anticipated = []
    for c in benchmark.get("negatives", []):
        r = _retrodict_one(c, edges, cutoff)
        if r["status"].startswith("anticipated"):
            false_anticipated.append({"gene": c.get("gene", c["locus"]),
                                      "locus": c["locus"], "target_terms": c.get("target_terms", [])})

    held_out = [p for p in positives if p["status"].startswith(("anticipated", "not_anticipable"))]
    anticipated = [p for p in positives if p["status"].startswith("anticipated")]
    metrics = {
        "cutoff": cutoff,
        "positives": len(positives),
        "known_by_cutoff": sum(1 for p in positives if p["status"] == "known_by_cutoff"),
        "held_out": len(held_out),
        "anticipated": len(anticipated),
        "anticipated_drug": sum(1 for p in positives if p["status"] == "anticipated_drug"),
        "anticipated_mechanism": sum(1 for p in positives if p["status"] == "anticipated_mechanism"),
        "not_anticipable": sum(1 for p in positives if p["status"] == "not_anticipable"),
        "unconfirmed": sum(1 for p in positives if p["status"] == "unconfirmed"),
        "anticipation_rate": round(len(anticipated) / len(held_out), 3) if held_out else 0.0,
        "false_anticipations": len(false_anticipated),  # headline: must be 0
        "clean": len(false_anticipated) == 0,
    }
    return {"organism": benchmark.get("organism", ""), "cutoff": cutoff,
            "metrics": metrics, "positives": positives,
            "false_anticipated": false_anticipated}


def _slim(edge: dict | None) -> dict | None:
    """Trim an edge to the fields the UI needs (target, year, provenance)."""
    if not edge:
        return None
    return {
        "relation": edge.get("relation"),
        "target": edge.get("target"),
        "year": _edge_year(edge),
        "grounded": bool(edge.get("grounded")),
        "provenance": edge.get("provenance") or {},
    }


def _match(control: dict, edges: list[dict]) -> dict | None:
    """Best edge supporting a control: grounded preferred, then abstract-only.

    An edge matches when it shares the control's locus + relation and its target text
    contains any of the control's target terms (case-insensitive). Pure.
    """
    terms = [t.lower() for t in control.get("target_terms", [])]
    grounded_hit: dict | None = None
    abstract_hit: dict | None = None
    for e in edges:
        if e.get("locus") != control["locus"]:
            continue
        if e.get("relation") != control["relation"]:
            continue
        target = (e.get("target") or "").lower()
        if terms and not any(term in target for term in terms):
            continue
        if e.get("grounded"):
            grounded_hit = grounded_hit or e
        else:
            abstract_hit = abstract_hit or e
    return grounded_hit or abstract_hit


def _classify(kind: str, support: dict | None) -> str:
    grounded = bool(support and support.get("grounded"))
    if kind == "positive":
        if grounded:
            return "recovered"
        return "literature_only" if support else "missing"
    # negative control
    if grounded:
        return "fabricated"
    return "weakly_asserted" if support else "refused"


def evaluate(benchmark: dict, edges: list[dict]) -> ValidationReport:
    """Check the grounded graph against the benchmark. Pure and deterministic."""
    items: list[ValidationItem] = []
    for kind, key in (("positive", "positives"), ("negative", "negatives")):
        for c in benchmark.get(key, []):
            support = _match(c, edges)
            status = _classify(kind, support)
            items.append(
                ValidationItem(
                    gene=c.get("gene", c["locus"]),
                    locus=c["locus"],
                    relation=c["relation"],
                    target_terms=c.get("target_terms", []),
                    kind=kind,
                    status=status,
                    matched_target=(support or {}).get("target"),
                    grounded=bool(support and support.get("grounded")),
                    provenance=(support or {}).get("provenance") or {},
                    expected_citation=c.get("citation"),
                    note=c.get("note") or c.get("reason"),
                )
            )

    pos = [i for i in items if i.kind == "positive"]
    neg = [i for i in items if i.kind == "negative"]
    recovered = sum(1 for i in pos if i.status == "recovered")
    literature_only = sum(1 for i in pos if i.status == "literature_only")
    missing = sum(1 for i in pos if i.status == "missing")
    refused = sum(1 for i in neg if i.status == "refused")
    fabricated = sum(1 for i in neg if i.status == "fabricated")
    weakly = sum(1 for i in neg if i.status == "weakly_asserted")

    metrics = {
        "positives": len(pos),
        "recovered": recovered,
        "literature_only": literature_only,
        "missing": missing,
        "recovery_rate": round(recovered / len(pos), 3) if pos else 0.0,
        "negatives": len(neg),
        "refused": refused,
        "fabricated": fabricated,  # headline: must be 0
        "weakly_asserted": weakly,
        "clean": fabricated == 0,
    }
    return ValidationReport(organism=benchmark.get("organism", ""), items=items, metrics=metrics)
