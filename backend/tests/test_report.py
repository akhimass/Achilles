"""Downloadable audit report (HTML) — pure checks.

The report must carry the real metrics, the fingerprint, one row per control, and the
embedded ledger for re-verification — and escape untrusted text.
"""

from __future__ import annotations

from app.audit import build_ledger, chain_head, observations_from_validation
from app.report import validation_report_html

_REPORT = {
    "metrics": {"recovered": 12, "positives": 12, "refused": 17, "negatives": 17,
                "fabricated": 0, "clean": True},
    "items": [
        {"gene": "MarR", "relation": "implicates", "target_terms": ["efflux"],
         "status": "recovered", "grounded": True,
         "provenance": {"acc": "ARO:3000718", "ref_url": "https://card.mcmaster.ca/x"}},
        {"gene": "MarR", "relation": "confers_resistance", "target_terms": ["vancomycin"],
         "status": "refused", "grounded": False, "provenance": {}},
    ],
}


def _html():
    ledger = build_ledger(observations_from_validation(_REPORT))
    return validation_report_html(_REPORT, ledger, chain_head(ledger), organism="Test org")


def test_report_has_metrics_fingerprint_and_rows():
    ledger = build_ledger(observations_from_validation(_REPORT))
    head = chain_head(ledger)
    h = validation_report_html(_REPORT, ledger, head, organism="Test org")
    assert "12/12" in h and "17/17" in h  # headline metrics
    assert head in h                       # the fingerprint is printed
    assert "MarR" in h and "vancomycin" in h and "recovered" in h and "refused" in h
    assert "/api/audit/verify" in h        # re-verify instructions
    assert 'id="achilles-ledger"' in h     # embedded ledger for verification


def test_report_escapes_untrusted_text():
    r = {"metrics": {"recovered": 1, "positives": 1, "refused": 0, "negatives": 0,
                     "fabricated": 0},
         "items": [{"gene": "<script>x</script>", "relation": "r", "target_terms": ["t"],
                    "status": "recovered", "provenance": {}}]}
    ledger = build_ledger(observations_from_validation(r))
    h = validation_report_html(r, ledger, chain_head(ledger))
    assert "<script>x</script>" not in h
    assert "&lt;script&gt;" in h
