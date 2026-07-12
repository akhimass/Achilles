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
