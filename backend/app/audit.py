"""Tamper-evident audit ledger — a receipt you can re-verify.

The self-validation result is deterministic: the same grounded graph always yields the
same recover/refuse/0-fabricated verdicts. This module turns that result into a
hash-CHAINED ledger — each entry's hash folds in the previous one — so any later edit to
any observation breaks the chain and is detectable. `verify_ledger` re-walks a ledger and
recomputes every hash from its own payload, so a downloaded report can be checked
independently: change one verdict and the chain no longer validates.

Pure and dependency-free (stdlib hashlib/json only) — trivially unit-testable, and the
same canonicalization must be used to build and to verify.
"""

from __future__ import annotations

import hashlib
import json

GENESIS = "0" * 64
_RESERVED = ("prev_hash", "entry_hash")


def canonical(obj) -> str:
    """Deterministic JSON: sorted keys, no whitespace — same input, same bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _entry_hash(payload: dict, prev: str) -> str:
    return sha256_hex(canonical(payload) + prev)


def build_ledger(observations: list[dict]) -> list[dict]:
    """Hash-chain an ordered list of observations. Pure.

    Each entry = the observation payload + `prev_hash` + `entry_hash`, where
    entry_hash = sha256(canonical(payload) + prev_hash). The chain starts from GENESIS.
    """
    ledger: list[dict] = []
    prev = GENESIS
    for i, obs in enumerate(observations):
        payload = {"index": i, **{k: v for k, v in obs.items() if k not in _RESERVED}}
        h = _entry_hash(payload, prev)
        ledger.append({**payload, "prev_hash": prev, "entry_hash": h})
        prev = h
    return ledger


def chain_head(ledger: list[dict]) -> str:
    """The single fingerprint of the whole ledger (last entry's hash)."""
    return ledger[-1]["entry_hash"] if ledger else GENESIS


def verify_ledger(ledger: list[dict]) -> dict:
    """Re-walk a ledger and recompute every hash from its own payload. Pure.

    Returns {valid, checked, break_at, head}. `break_at` is the first index whose stored
    hash disagrees with the recomputation (i.e. the observation was tampered with), or None.
    """
    prev = GENESIS
    for i, e in enumerate(ledger):
        payload = {k: v for k, v in e.items() if k not in _RESERVED}
        expected = _entry_hash(payload, prev)
        if e.get("prev_hash") != prev or e.get("entry_hash") != expected:
            return {"valid": False, "checked": i, "break_at": i, "head": chain_head(ledger)}
        prev = e["entry_hash"]
    return {"valid": True, "checked": len(ledger), "break_at": None, "head": prev}


def observations_from_validation(report: dict) -> list[dict]:
    """Flatten a ValidationReport into ordered, ledger-ready observations. Pure."""
    obs: list[dict] = []
    for it in report.get("items", []):
        prov = it.get("provenance") or {}
        obs.append({
            "kind": it.get("kind"),
            "gene": it.get("gene"),
            "locus": it.get("locus"),
            "relation": it.get("relation"),
            "target_terms": it.get("target_terms", []),
            "verdict": it.get("status"),
            "grounded": bool(it.get("grounded")),
            "citation": prov.get("acc") or prov.get("pmid"),
        })
    return obs
