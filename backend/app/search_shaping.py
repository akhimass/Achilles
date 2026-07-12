"""Deterministic retrieval over the evidence graph — the search DB the LLM uses.

Turns a free-text query into a ranked, GROUNDED result set across the three corpora
that make up the graph: papers (title + abstract), genes (name + product + locus), and
evidence edges (the extracted claim + its supporting span). Every result carries its
provenance (PMID / reference accession), so retrieval never returns an unsourced claim
— the same discipline as the rest of Achilles.

Ranking is a small, transparent lexical scorer (term frequency × field weight, with a
grounded-provenance boost). It is pure and unit-tested; the router does the SQL and
hands rows here. A pgvector semantic path (ai/embeddings.py) layers on top when paper
embeddings are populated — this module is the deterministic core that always works,
offline and network-free.
"""

from __future__ import annotations

import re

from app.graph_shaping import claim_sentence, pubmed_url, reference_url

_TOKEN = re.compile(r"[a-z0-9]+")
# Field weights: a hit in a title/name/claim counts more than one deep in an abstract.
_W_TITLE = 3.0
_W_BODY = 1.0
_GROUNDED_BOOST = 1.15  # results with full provenance rank slightly higher


def tokenize(text: str | None) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _score(query_terms: list[str], title: str | None, body: str | None) -> float:
    """Lexical relevance: Σ term-frequency, title-weighted. Deterministic."""
    if not query_terms:
        return 0.0
    tset = set(query_terms)
    title_toks = [t for t in tokenize(title) if t in tset]
    body_toks = [t for t in tokenize(body) if t in tset]
    score = _W_TITLE * len(title_toks) + _W_BODY * len(body_toks)
    # Reward covering more distinct query terms (not just one term repeated).
    covered = len(tset & (set(title_toks) | set(body_toks)))
    return score * (1.0 + 0.5 * covered)


def _snippet(text: str | None, query_terms: list[str], width: int = 160) -> str | None:
    """A short excerpt around the first query-term hit (deterministic)."""
    if not text:
        return None
    low = text.lower()
    pos = -1
    for t in query_terms:
        i = low.find(t)
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return text[:width].strip() + ("…" if len(text) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    return ("…" if start > 0 else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def paper_candidate(r: dict) -> dict:
    pmid = r.get("pmid")
    return {
        "kind": "paper",
        "id": pmid or (str(r.get("id")) if r.get("id") else None),
        "title": r.get("title"),
        "_title": r.get("title"),
        "_body": r.get("abstract"),
        "grounded": bool(pmid),
        "provenance": {"pmid": pmid, "pubmed_url": pubmed_url(pmid),
                       "db": None, "acc": None, "ref_url": None},
        "extra": {"year": r.get("year")},
    }


def gene_candidate(r: dict) -> dict:
    locus = r.get("locus_tag")
    name = r.get("name")
    return {
        "kind": "gene",
        "id": locus,
        "title": f"{name} ({locus})" if name else locus,
        "_title": " ".join(filter(None, [name, locus])),
        "_body": r.get("product"),
        "grounded": True,  # reference-annotation gene
        "provenance": {"pmid": None, "pubmed_url": None, "db": "UniProt",
                       "acc": r.get("uniprot_acc"),
                       "ref_url": reference_url("UniProt", r.get("uniprot_acc"))},
        "extra": {"locus_tag": locus, "product": r.get("product")},
    }


def edge_candidate(r: dict) -> dict:
    meta = r.get("metadata") or {}
    subject = meta.get("subject")
    target = r.get("target_literal")
    claim = claim_sentence(subject, r.get("relation"), target)
    pmid = r.get("provenance_pmid")
    db = r.get("provenance_db")
    acc = r.get("provenance_acc")
    return {
        "kind": "edge",
        "id": str(r.get("id")) if r.get("id") else None,
        "title": claim,
        "_title": claim,
        "_body": meta.get("evidence_span"),
        "grounded": bool(r.get("grounded")),
        "provenance": {"pmid": pmid, "pubmed_url": pubmed_url(pmid), "db": db, "acc": acc,
                       "ref_url": reference_url(db, acc)},
        "extra": {"relation": r.get("relation"), "confidence": r.get("confidence"),
                  "gene_locus": meta.get("gene_locus")},
    }


def rank_results(query: str, candidates: list[dict], *, limit: int = 20) -> list[dict]:
    """Score, filter, and order candidates for a query. Pure and deterministic.

    Zero-score candidates are dropped (never padded). Grounded results get a small
    boost. Ties break by kind then id so ordering never depends on input order.
    """
    terms = tokenize(query)
    scored: list[dict] = []
    for c in candidates:
        base = _score(terms, c.get("_title"), c.get("_body"))
        if base <= 0:
            continue
        s = round(base * (_GROUNDED_BOOST if c.get("grounded") else 1.0), 4)
        scored.append(
            {
                "kind": c["kind"],
                "id": c.get("id"),
                "title": c.get("title"),
                "snippet": _snippet(c.get("_body") or c.get("_title"), terms),
                "score": s,
                "grounded": bool(c.get("grounded")),
                "provenance": c.get("provenance") or {},
                "extra": c.get("extra") or {},
            }
        )
    scored.sort(key=lambda r: (-r["score"], r["kind"], str(r.get("id"))))
    return scored[:limit]


def shape_search(query: str, candidates: list[dict], *, limit: int = 20, mode: str = "lexical") -> dict:
    """Full /api/search payload: ranked grounded results + counts. Pure."""
    results = rank_results(query, candidates, limit=limit)
    grounded = sum(1 for r in results if r["grounded"])
    by_kind: dict[str, int] = {}
    for r in results:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    return {
        "query": query,
        "mode": mode,  # 'lexical' (deterministic) | 'semantic' (pgvector)
        "results": results,
        "counts": {"total": len(results), "grounded": grounded, "by_kind": by_kind},
    }
