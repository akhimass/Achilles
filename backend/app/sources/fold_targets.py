"""Fold EVERY ranked target with Tamarind Bio — full AlphaFold coverage of the target set.

The demo ships one committed structure (MarR). This uses Tamarind across *all* candidate
targets: for each target locus it resolves a protein sequence (NCBI WP if available, else
UniProt by accession), submits an AlphaFold job (validate → submit), polls to completion,
downloads the PDB, and caches it under data/demo/structures/ keyed exactly as
/api/structure reads it — so every target card gets a live 3D structure.

Requires TAMARIND_API_KEY (and network). Run once:  python -m app.sources.fold_targets
Public proteins only. Structures are cached (committable, public).
"""

from __future__ import annotations

import asyncio
import json
import re

from app.ai import tamarind
from app.config import settings
from app.ingestion.seed import PUBLIC_REFERENCE_GENES
from app.ingestion.seed_targets import TARGET_MECHANISM, TARGET_UNIPROT

_WP_BY_LOCUS = {g["locus_tag"]: g.get("wp") for g in PUBLIC_REFERENCE_GENES}
_NAME_BY_LOCUS = {g["locus_tag"]: g.get("name") for g in PUBLIC_REFERENCE_GENES}


async def _sequence_for(locus: str, acc: str) -> str | None:
    wp = _WP_BY_LOCUS.get(locus)
    seq = await tamarind.fetch_protein_sequence(wp) if wp else None
    if not seq and acc:
        seq = await tamarind.fetch_uniprot_sequence(acc)
    return seq


async def fold_all() -> None:
    if not settings.tamarind_api_key:
        print(
            "fold_targets: no TAMARIND_API_KEY set — nothing folded.\n"
            "  Set TAMARIND_API_KEY and re-run to fold every target via Tamarind AlphaFold."
        )
        return

    folded, pending, skipped = 0, 0, 0
    for locus, acc in TARGET_UNIPROT.items():
        wp = _WP_BY_LOCUS.get(locus)
        cache_key = wp or locus
        cache_file = tamarind._cache_dir() / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', cache_key)}.json"
        if cache_file.exists():
            print(f"  {locus}: cached ({cache_key}) — skip")
            skipped += 1
            continue

        seq = await _sequence_for(locus, acc)
        if not seq:
            print(f"  {locus}: no sequence (wp={wp}, uniprot={acc}) — skip")
            continue

        job = tamarind._job_name(locus)
        state, url = await tamarind.poll_job(job, max_wait=0)
        if state not in ("complete", "running"):
            ok = await tamarind.submit_alphafold(seq, job)
            print(f"  {locus}: submitted AlphaFold job '{job}' ({'ok' if ok else 'FAILED'})")

        # Poll to completion (bounded by config), then download + cache.
        state, url = await tamarind.poll_job(
            job, max_wait=settings.tamarind_poll_max_seconds, interval=15
        )
        if state == "complete":
            pdb = await tamarind.download_result(job, result_url=url)
            if pdb:
                payload = tamarind._complete_payload(
                    locus, wp, _NAME_BY_LOCUS.get(locus), TARGET_MECHANISM.get(locus), pdb, job
                )
                cache_file.write_text(json.dumps(payload))
                folded += 1
                print(f"  {locus}: folded → {cache_file.name} (pLDDT {payload['plddt']})")
            else:
                print(f"  {locus}: complete but download failed")
        else:
            pending += 1
            print(f"  {locus}: job state '{state}' — re-run later to collect")

    print(f"fold_targets: {folded} folded, {pending} pending, {skipped} cached "
          f"(of {len(TARGET_UNIPROT)} targets)")


if __name__ == "__main__":
    asyncio.run(fold_all())
