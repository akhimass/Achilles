"""Tamper-evident audit ledger — pure checks.

The invariants: the fingerprint is deterministic, a clean ledger verifies, and editing any
observation breaks the chain at exactly that entry.
"""

from __future__ import annotations

from app.audit import (
    build_ledger,
    chain_head,
    observations_from_validation,
    verify_ledger,
)

_OBS = [
    {"kind": "positive", "gene": "MarR", "verdict": "recovered", "grounded": True,
     "citation": "ARO:3000718"},
    {"kind": "positive", "gene": "AraC/MarA", "verdict": "recovered", "grounded": True,
     "citation": "ARO:3000823"},
    {"kind": "negative", "gene": "MarR", "verdict": "refused", "grounded": False,
     "citation": None},
]


def test_ledger_is_deterministic():
    a = chain_head(build_ledger(_OBS))
    b = chain_head(build_ledger(_OBS))
    assert a == b and len(a) == 64  # same input → same sha256 fingerprint


def test_clean_ledger_verifies():
    ledger = build_ledger(_OBS)
    v = verify_ledger(ledger)
    assert v["valid"] is True
    assert v["checked"] == 3 and v["break_at"] is None
    assert v["head"] == chain_head(ledger)


def test_tamper_breaks_the_chain_at_that_entry():
    ledger = build_ledger(_OBS)
    # flip a verdict on entry 1 WITHOUT recomputing its hash — a forged report
    ledger[1]["verdict"] = "fabricated"
    v = verify_ledger(ledger)
    assert v["valid"] is False
    assert v["break_at"] == 1


def test_reordering_breaks_the_chain():
    ledger = build_ledger(_OBS)
    ledger[0], ledger[1] = ledger[1], ledger[0]
    assert verify_ledger(ledger)["valid"] is False


def test_observations_from_validation_shape():
    report = {"items": [
        {"kind": "positive", "gene": "MarR", "locus": "L1", "relation": "implicates",
         "target_terms": ["efflux"], "status": "recovered", "grounded": True,
         "provenance": {"acc": "ARO:1", "pmid": "9"}},
    ]}
    obs = observations_from_validation(report)
    assert obs[0]["verdict"] == "recovered" and obs[0]["citation"] == "ARO:1"
    # ledger built from it verifies
    assert verify_ledger(build_ledger(obs))["valid"] is True
