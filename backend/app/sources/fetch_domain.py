"""Fetch a domain's real PubMLST isolates → committed snapshot (network; run locally).

This is the first, concrete step of ingesting a NEW domain: it pulls real, dated isolates
with full MLST profiles from that domain's PubMLST database (per its registry config) and
writes data/demo/<snapshot>.json — the same shape the deterministic lineage/flipper core
already consumes. No fabrication: every isolate + allele profile is real public data.

Usage (needs network):
    python -m app.sources.fetch_domain pseudomonas
    python -m app.sources.fetch_domain pseudomonas --limit 60

After this, populate the domain's reference-gene catalog from NCBI/UniProt (see
docs/ADDING_A_DOMAIN.md), then seed. Reference genes are never invented.
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.ingestion.domains import get_domain
from app.sources.pubmlst import fetch_domain_isolates


async def fetch_and_write(domain_key: str, *, limit: int = 70, scan: int = 250) -> None:
    domain = get_domain(domain_key)
    if not domain.pubmlst_snapshot:
        raise SystemExit(f"domain '{domain.key}' has no snapshot filename configured.")
    print(f"fetching {domain.organism} isolates from {domain.pubmlst_isolates_db} …")
    records = await fetch_domain_isolates(domain, limit=limit, scan=scan)
    if not records:
        raise SystemExit(
            "no complete, dated isolates returned — check the PubMLST db/scheme in the "
            "domain config, or widen --scan."
        )
    snapshot = {
        "meta": {
            "organism": domain.organism,
            "n_isolates": len(records),
            "loci": list(domain.mlst_loci),
            "provenance": f"PubMLST — {domain.organism} isolates database",
            "source_url": domain.pubmlst_isolates_db,
            "citation": "Jolley KA, Bray JE, Maiden MCJ (2018), pubmlst.org (public).",
            "note": "Real isolates + real MLST allele profiles; lineage is reconstructed "
                    "deterministically and is not a validated phylogeny.",
        },
        "records": records,
    }
    out = domain.snapshot_path
    out.write_text(json.dumps(snapshot, indent=2))
    print(f"wrote {out}  ({len(records)} isolates, {len(domain.mlst_loci)} loci)")
    print("next: populate reference genes from NCBI/UniProt (docs/ADDING_A_DOMAIN.md), then seed.")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    if not args:
        raise SystemExit("usage: python -m app.sources.fetch_domain <domain_key> [--limit N] [--scan N]")
    key = args[0]
    limit = _int_flag(args, "--limit", 70)
    scan = _int_flag(args, "--scan", 250)
    asyncio.run(fetch_and_write(key, limit=limit, scan=scan))


def _int_flag(args: list[str], flag: str, default: int) -> int:
    if flag in args:
        try:
            return int(args[args.index(flag) + 1])
        except (IndexError, ValueError):
            pass
    return default


if __name__ == "__main__":
    main()
