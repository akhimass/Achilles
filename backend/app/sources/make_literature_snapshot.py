"""Build the committed literature evidence corpus (public sources only).

    cd backend && python -m app.sources.make_literature_snapshot

Pipeline (runs once, with network + an Anthropic key), producing a committed,
offline artifact:

    Europe PMC (scoped, per gene) -> ai.extraction (typed claims) ->
    CARD/ARO + UniProt grounding -> deterministic decide_edge -> corpus.json

`make seed` then replays corpus.json with ZERO network/LLM. Everything committed is
public: PubMed abstracts, ARO/UniProt reference facts, and edges keyed to public
gene symbols/locus tags. The private strain data (BurkData) is never touched here.

Raw Europe PMC responses cache under data/demo/literature/raw/, and extraction /
grounding results under data/demo/literature/llmcache/, so re-runs are cheap/offline.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path

from uuid import NAMESPACE_URL, uuid5

from app.ai.extraction import ExtractedClaim, ExtractionResult, extract_claims
from app.ai.grounding import GroundingVerdict, decide_edge, ground_claim
from app.config import settings
from app.ingestion.domains import get_domain
from app.ingestion.seed import _burk_gene_id
from app.models.domain import EvidenceEdge, Paper
from app.sources import europepmc

ORGANISM = "Burkholderia multivorans"
LIT_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "literature"
RAW_DIR = LIT_DIR / "raw"
LLM_DIR = LIT_DIR / "llmcache"
SNAPSHOT = LIT_DIR / "corpus.json"

# Corpus scoped to real seeded flipper-gene FAMILIES (public identities). A paper
# counts only if its text is about the family (`topic` regex) — homology-based, the
# way AMR annotation transfers mechanism across organisms. Grounding then corroborates
# the family→drug link in CARD/ARO + UniProt (`ground_symbol`). Burkholderia is the
# organism of interest; mechanism evidence is drawn from the family's literature.
CORPUS: list[dict] = [
    {
        "locus": "A8H40_RS07590",
        "symbol": "MarR",
        "ground_symbol": "MarR",
        "queries": [
            "MarR regulator multidrug efflux resistance",
            "MarR family transcriptional regulator antibiotic resistance",
            "Burkholderia MarR efflux resistance",
        ],
        "topic": r"\bmar[rab]?\b|mar[- ]?family|mar operon|mar regulon",
    },
    {
        "locus": "A8H40_RS24275",
        "symbol": "AraC/MarA-family activator",
        "ground_symbol": "RamA",
        "queries": [
            "AraC family multidrug resistance activator efflux MarA RamA SoxS",
            "Burkholderia AraC regulator multidrug resistance",
        ],
        "topic": r"\barac\b|arac[- ]?family|\bmara\b|\bram[ar]\b|\bsox[rs]\b|\brob\b",
    },
    {
        "locus": "A8H40_RS17945",
        "symbol": "LysR-family regulator",
        "ground_symbol": "LysR",
        "queries": [
            "LysR family transcriptional regulator antibiotic resistance efflux",
            "Burkholderia LysR regulator resistance",
        ],
        "topic": r"\blysr\b|lysr[- ]?family|lysr[- ]?type",
    },
    {
        "locus": "A8H40_RS19975",
        "symbol": "drug/efflux transporter",
        "ground_symbol": "efflux pump",
        "queries": [
            "RND efflux pump multidrug resistance Gram-negative",
            "Burkholderia efflux pump antibiotic resistance",
        ],
        "topic": r"efflux|\brnd\b|multidrug transporter|drug transporter|\bmex[a-z]?\b|\bacr[ab]\b",
    },
    {
        "locus": "A8H40_RS00780",
        "symbol": "two-component response regulator",
        "ground_symbol": "response regulator",
        "queries": [
            "two-component response regulator antibiotic resistance",
            "Burkholderia two-component system antibiotic resistance",
        ],
        "topic": r"response regulator|two[- ]?component",
    },
]

# Only these relations are meaningful resistance evidence for a gene→drug edge.
_KEEP_RELATIONS = {"confers_resistance", "sensitizes_to", "is_target_of", "implicates"}
# Cap edges per gene so the panel stays legible and the corpus bounded.
MAX_EDGES_PER_GENE = 24


def _corpus_for_domain(domain) -> list[dict]:
    """Build a corpus spec (per-gene queries + topic regex) for ANY domain from its
    registry config. Pure. Burkholderia keeps its hand-tuned CORPUS above (so the
    committed corpus reproduces byte-for-byte); other domains are derived from their
    reference-gene catalog + literature query. Empty when reference genes aren't yet
    populated — the builder then exits rather than invent a corpus.
    """
    if domain.key == "burkholderia":
        return CORPUS
    spec: list[dict] = []
    for g in domain.reference_genes:
        sym = g.get("name") or g.get("locus_tag")
        # a permissive topic regex from the gene symbol's alphanumeric tokens
        toks = [t for t in re.split(r"[^a-z0-9]+", (sym or "").lower()) if len(t) >= 3]
        topic = "|".join(re.escape(t) for t in toks) or re.escape((sym or "gene").lower())
        spec.append({
            "locus": g["locus_tag"],
            "symbol": sym,
            "ground_symbol": sym,
            "queries": [f"{domain.organism} {sym} resistance efflux", domain.europepmc_query],
            "topic": topic,
        })
    return spec


def _is_topical(paper: Paper, topic: str) -> bool:
    text = f"{paper.title}\n{paper.abstract or ''}".lower()
    return re.search(topic, text) is not None


def _read(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2))


def _slug(s: str) -> str:
    h = hashlib.md5(s.encode(), usedforsecurity=False).hexdigest()[:10]
    return h


async def _fetch_raw(query: str, limit: int) -> list[dict]:
    cache = RAW_DIR / f"epmc-{_slug(query)}.json"
    cached = _read(cache)
    if cached is not None:
        return cached
    raw = await europepmc.fetch_raw(query, limit=limit)
    _write(cache, raw)
    return raw


async def _retry(coro_factory, attempts: int = 3):
    """Run an async LLM call with small backoff — smooths transient empty/429 replies."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as exc:  # noqa: BLE001
            last = exc
            await asyncio.sleep(1.5 * (i + 1))
    raise last  # type: ignore[misc]


async def _extract(paper: Paper) -> ExtractionResult:
    cache = LLM_DIR / f"extract-{paper.pmid}.json"
    cached = _read(cache)
    if cached is not None:
        return ExtractionResult.model_validate(cached)
    result = await _retry(lambda: extract_claims(paper))
    _write(cache, result.model_dump())
    return result


async def _ground(claim: ExtractedClaim, organism: str, *, gene_term: str) -> GroundingVerdict:
    key = f"{gene_term}|{claim.relation}|{claim.object}|{organism}"
    cache = LLM_DIR / f"ground-{_slug(key)}.json"
    cached = _read(cache)
    if cached is not None:
        return GroundingVerdict.model_validate(cached)
    verdict = await _retry(lambda: ground_claim(claim, organism, gene_term=gene_term))
    _write(cache, verdict.model_dump())
    return verdict


async def harvest_gene(
    entry: dict, organism: str, *, per_query_limit: int = 30, gene_id_fn=_burk_gene_id
) -> tuple[dict[str, Paper], list[tuple[EvidenceEdge, Paper]]]:
    """Fetch → extract → ground → decide for one gene. Returns its papers + edges."""
    papers: dict[str, Paper] = {}
    for q in entry["queries"]:
        for hit in await _fetch_raw(q, per_query_limit):
            p = europepmc.hit_to_paper(hit)
            if p and p.pmid:
                papers.setdefault(p.pmid, p)

    # Keep only papers whose text is actually about this gene family.
    topical = {pmid: p for pmid, p in papers.items() if _is_topical(p, entry["topic"])}

    topic = entry["topic"]
    gene_id = gene_id_fn(entry["locus"])
    ground_symbol = entry.get("ground_symbol", entry["symbol"])
    extracted_by = f"ai/extraction.py@{settings.model_extract}"
    candidates: list[tuple[EvidenceEdge, Paper]] = []
    for paper in topical.values():
        try:
            result = await _extract(paper)
        except Exception as exc:  # noqa: BLE001 — skip a bad paper, keep building
            print(f"  ! extract failed pmid={paper.pmid}: {exc}")
            continue
        for claim in result.claims:
            if claim.relation not in _KEEP_RELATIONS:
                continue
            # The claim's SUBJECT must be this gene family — not just any gene named
            # in a topical paper — so the edge is truthfully about this gene.
            if not re.search(topic, (claim.subject or "").lower()):
                continue
            try:
                verdict = await _ground(claim, organism, gene_term=ground_symbol)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! ground failed: {exc}")
                verdict = None
            edge = decide_edge(
                claim,
                verdict,
                gene_id=gene_id,
                gene_symbol=entry["symbol"],
                gene_locus=entry["locus"],
                paper_pmid=paper.pmid,
                extracted_by=extracted_by,
            )
            if edge:
                candidates.append((edge, paper))

    # Dedupe identical (subject, relation, target) across papers — keep the strongest
    # (grounded first, then confidence) — then cap.
    best: dict[tuple, tuple[EvidenceEdge, Paper]] = {}
    for edge, paper in candidates:
        k = (
            (edge.metadata.get("subject") or "").lower(),
            edge.relation.value,
            (edge.target_literal or "").lower(),
        )
        cur = best.get(k)
        if cur is None or (edge.grounded, edge.confidence) > (cur[0].grounded, cur[0].confidence):
            best[k] = (edge, paper)
    edges = sorted(best.values(), key=lambda ep: (not ep[0].grounded, -ep[0].confidence))[
        :MAX_EDGES_PER_GENE
    ]
    return topical, edges


def _serialize_edge(edge: EvidenceEdge, paper: Paper) -> dict:
    d = edge.model_dump(mode="json")
    d["gene_locus"] = edge.metadata.get("gene_locus")
    d["paper_title"] = paper.title
    d["paper_year"] = paper.year
    return d


async def build(domain_key: str = "burkholderia") -> dict:
    """Build a domain's literature corpus. Burkholderia (default) reproduces the committed
    corpus.json byte-for-byte. Any other registered domain builds from its reference-gene
    catalog + literature query, writing data/demo/literature/<key>_corpus.json.
    """
    domain = get_domain(domain_key)
    corpus = _corpus_for_domain(domain)
    if not corpus:
        print(
            f"make-corpus: domain '{domain.key}' has no reference genes to harvest — "
            "populate its reference_genes (real NCBI/UniProt accessions) first "
            "(see DRIVE_B.md). Nothing built; nothing fabricated."
        )
        return {}
    organism = domain.organism
    snapshot_path = SNAPSHOT if domain.key == "burkholderia" else LIT_DIR / f"{domain.key}_corpus.json"
    gene_id_fn = (
        _burk_gene_id
        if domain.key == "burkholderia"
        else (lambda locus: uuid5(NAMESPACE_URL, f"achilles/gene/{organism}/{locus}"))
    )

    all_papers: dict[str, Paper] = {}
    all_edges: list[dict] = []
    per_gene: dict[str, int] = {}
    for entry in corpus:
        print(f"harvesting {entry['symbol']} ({entry['locus']}) …")
        papers, edges = await harvest_gene(entry, organism, gene_id_fn=gene_id_fn)
        all_papers.update(papers)
        all_edges.extend(_serialize_edge(e, p) for e, p in edges)
        per_gene[entry["locus"]] = len(edges)
        print(f"  {len(papers)} papers, {len(edges)} edges")

    grounded = sum(1 for e in all_edges if e["grounded"])
    snapshot = {
        "meta": {
            "organism": organism,
            "source": "Europe PMC (abstracts) + CARD/ARO + UniProt (grounding)",
            "note": "Public data only. Edges keyed to public gene symbols/locus tags.",
            "n_papers": len(all_papers),
            "n_edges": len(all_edges),
            "n_grounded": grounded,
            "pct_grounded": round(100 * grounded / len(all_edges), 1) if all_edges else 0.0,
            "edges_per_gene": per_gene,
            "queries": [q for e in corpus for q in e["queries"]],
        },
        "papers": [p.model_dump(mode="json") for p in all_papers.values()],
        "edges": all_edges,
    }
    _write(snapshot_path, snapshot)
    m = snapshot["meta"]
    print(
        f"\ncorpus ({organism}): {m['n_papers']} papers, {m['n_edges']} edges "
        f"({m['pct_grounded']}% grounded) -> {snapshot_path}"
    )
    return snapshot


if __name__ == "__main__":
    import sys

    _key = "burkholderia"
    if "--domain" in sys.argv:
        _key = sys.argv[sys.argv.index("--domain") + 1]
    asyncio.run(build(_key))
