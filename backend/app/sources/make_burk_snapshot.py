"""Build the committed BurkData demo snapshot (reads the local BurkData tree).

    cd backend && python -m app.sources.make_burk_snapshot

Reads the real experimental-evolution dataset and writes a normalized, offline
snapshot to data/demo/. `ingestion/seed.py` consumes it with no filesystem
dependency on BurkData, so the demo is reproducible even without that tree.
Override the BurkData location with BURKDATA_DIR.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.sources.burkdata import load_records

SNAPSHOT = Path(__file__).resolve().parents[3] / "data" / "demo" / "bmultivorans_burkdata.json"


def main() -> None:
    records = load_records(top_flipper_genes=60)
    snapshot = {
        "meta": {
            "organism": records["organism"],
            "provenance": "Burkholderia multivorans experimental-evolution record (BurkData: SnpFlip/IndelFlip)",
            "reference": "NCBI GCF_001718455 / NZ_CP020397-9; gene indels vs reference",
            "n_strains": len(records["strain_ids"]),
            "n_lineages": len(records["lineages"]),
            "n_flipper_genes_shown": len(records["genes"]),
            "n_flipper_genes_total": records["n_flipper_genes_total"],
            "note": (
                "Real isolates and real experimental lineages (not reconstructed). "
                "Flipper genes = genes whose indel presence reverses along a lineage."
            ),
        },
        **records,
    }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    print(
        f"snapshot: {snapshot['meta']['n_strains']} strains, "
        f"{snapshot['meta']['n_lineages']} lineages, "
        f"{snapshot['meta']['n_flipper_genes_shown']} flipper genes "
        f"(of {snapshot['meta']['n_flipper_genes_total']}) -> {SNAPSHOT}"
    )


if __name__ == "__main__":
    main()
