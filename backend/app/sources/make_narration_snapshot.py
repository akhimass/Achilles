"""Build the committed narration cache — run ONCE by a maintainer with an API key.

Produces pre-reviewed, cited LLM narration for the demo targets and writes it to
``data/demo/narration/targets.json`` so the app can serve fixed, reproducible
narration without a live call per visitor (see ``app/ai/narration_cache.py``).

Data rights (important):
  - TARGET rationales derive from the PUBLIC literature corpus + public ChEMBL, so
    ``targets.json`` is safe to commit.
  - CYCLE narration derives from the private BurkData collateral record. It is
    therefore LOCAL-ONLY and is NEVER written here or committed. On the public
    deployment the cycle is empty anyway, so its narration is moot.

Requires ANTHROPIC_API_KEY. If absent, this prints how to set it and writes nothing —
we never fabricate narration. Run:  python -m app.sources.make_narration_snapshot
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.ai.narration_cache import NARRATION_DIR, TARGETS_FILE
from app.config import settings
from app.graph_shaping import pubmed_url, reference_url  # noqa: F401 (kept for parity)
from app.ingestion.scoring import GeneEvidenceStats, rank_targets
from app.ingestion.seed_targets import TARGET_MECHANISM, TARGET_UNIPROT
from app.sources import chembl

_CORPUS = Path(__file__).resolve().parents[2] / "data" / "demo" / "literature" / "corpus.json"


def _gene_stats() -> tuple[list[GeneEvidenceStats], dict[str, list[dict]]]:
    """Aggregate the committed public corpus into per-gene stats + edges (no DB)."""
    corpus = json.loads(_CORPUS.read_text())
    agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "conf": 0.0, "grounded": 0})
    edges: dict[str, list[dict]] = defaultdict(list)
    for e in corpus.get("edges", []):
        loc = e.get("gene_locus") or (e.get("metadata") or {}).get("gene_locus")
        if not loc:
            continue
        a = agg[loc]
        a["n"] += 1
        a["conf"] += e.get("confidence", 0.0)
        a["grounded"] += 1 if e.get("grounded") else 0
        edges[loc].append(e)
    stats = [
        GeneEvidenceStats(
            gene_id=loc,
            locus_tag=loc,
            n_edges=a["n"],
            mean_confidence=(a["conf"] / a["n"]) if a["n"] else 0.0,
            grounded_edges=a["grounded"],
            flipper_support=0,  # public path has no flipper support for these loci
        )
        for loc, a in agg.items()
    ]
    return stats, edges


def _edges_text(edges: list[dict]) -> str:
    lines = []
    for e in sorted(edges, key=lambda x: (not x.get("grounded"), -x.get("confidence", 0)))[:6]:
        prov = e.get("provenance_db") or "PMID"
        acc = e.get("provenance_acc") or e.get("provenance_pmid")
        lines.append(
            f"- {e.get('relation')} {e.get('target_literal')} "
            f"(conf {e.get('confidence', 0):.2f}, "
            f"{'grounded' if e.get('grounded') else 'ungrounded'}; {prov}:{acc})"
        )
    return "\n".join(lines) or "(none)"


async def main() -> None:
    if not settings.anthropic_api_key:
        print(
            "make_narration_snapshot: no ANTHROPIC_API_KEY set — nothing written.\n"
            "  Set ANTHROPIC_API_KEY and re-run to generate the committed target\n"
            "  narration cache. (We never fabricate narration.)"
        )
        return

    from app.ai.targets import narrate_target

    stats, edges = _gene_stats()
    targets = rank_targets(stats)
    out: dict = {}
    for t in targets:
        locus = t.locus_tag
        acc = TARGET_UNIPROT.get(locus)
        tract = chembl.tractability_from_cache(acc)
        tract_txt = (
            "no known ChEMBL chemical matter (novel)"
            if tract.get("assessed") and not tract.get("has_target")
            else str(tract)
        )
        result = await narrate_target(
            gene=locus,
            product=TARGET_MECHANISM.get(locus, ""),
            rank_score=t.rank_score,
            edges=_edges_text(edges.get(locus, [])),
            tractability=tract_txt,
        )
        out[locus] = {
            "narrative": result.narrative,
            "citations": list(result.citations or []),
            "model": settings.model_reason,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        print(f"  narrated {locus} ({len(result.citations or [])} citations)")

    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    TARGETS_FILE.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"make_narration_snapshot: wrote {len(out)} target rationales → {TARGETS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
