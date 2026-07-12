"""Regenerate the committed offline demo snapshot from PubMLST (network).

Run manually to refresh `data/demo/bmultivorans_pubmlst.json`:

    cd backend && python -m app.sources.make_snapshot

This is the only place the demo touches the network. `ingestion/seed.py` reads the
committed snapshot offline, so `make seed` never fetches. Raw per-isolate responses
are cached under `data/pubmlst/`, so re-running is fast and reproducible.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.sources.pubmlst import build_snapshot, fetch_isolates

ORGANISM = "Burkholderia multivorans"
SNAPSHOT = Path(__file__).resolve().parents[3] / "data" / "demo" / "bmultivorans_pubmlst.json"


async def main() -> None:
    records = await fetch_isolates(ORGANISM, limit=70)
    snapshot = build_snapshot(records, ORGANISM)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2))
    print(f"snapshot: {len(records)} isolates -> {SNAPSHOT}")


if __name__ == "__main__":
    asyncio.run(main())
