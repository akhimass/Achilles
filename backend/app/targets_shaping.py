"""Pure view-model transforms for the target-ranking endpoint (Phase 3).

Kept free of DB / LLM / driver imports so the shaping — including the deterministic,
citation-backed rationale — is unit-testable on its own. The router runs the SQL and
hands rows here; `ai/targets.py` may replace the rationale with an LLM narration, but
never the rank_score.
"""

from __future__ import annotations

from app.graph_shaping import pubmed_url, reference_url

_MAX_EVIDENCE = 6  # top edges surfaced per target
_RELATION_VERB = {
    "confers_resistance": "confers resistance to",
    "sensitizes_to": "sensitizes to",
    "is_target_of": "is targeted by",
    "implicates": "implicates",
    "reverts_with": "reverts with",
}


def shape_evidence_edge(r: dict) -> dict:
    """One evidence edge → the compact view shape (mirrors graph_shaping.shape_evidence)."""
    meta = r.get("metadata") or {}
    pmid = r.get("provenance_pmid")
    acc = r.get("provenance_acc")
    db = r.get("provenance_db")
    return {
        "relation": r["relation"],
        "target": r.get("target_literal") or (str(r["target_id"]) if r.get("target_id") else None),
        "target_type": r.get("target_type"),
        "confidence": float(r["confidence"]),
        "grounded": bool(r["grounded"]),
        "subject": meta.get("subject"),
        "evidence_span": meta.get("evidence_span"),
        "provenance": {
            "pmid": pmid,
            "pubmed_url": pubmed_url(pmid),
            "db": db,
            "acc": acc,
            "ref_url": reference_url(db, acc),
            "paper_title": r.get("paper_title"),
            "paper_year": r.get("paper_year"),
        },
    }


def _sorted_edges(edges: list[dict]) -> list[dict]:
    return sorted(edges, key=lambda e: (not e["grounded"], -e["confidence"]))


def _citation_id(edge: dict) -> str | None:
    prov = edge["provenance"]
    if prov.get("db") and prov.get("acc"):
        return f"{prov['db']}:{prov['acc']}"
    if prov.get("pmid"):
        return f"PMID:{prov['pmid']}"
    return None


def deterministic_rationale(target: dict, edges: list[dict]) -> tuple[str, list[str]]:
    """Compose a factual, cited rationale from real edges + tractability (no LLM).

    Every clause is backed by data already in the graph; citations are the real PMIDs
    and reference accessions of the edges used. This is the offline-reproducible
    rationale; the LLM narration (when a key is configured) can replace it, but the
    facts and the rank_score never change.
    """
    locus = target.get("locus_tag") or ""
    label = target.get("name") or locus or "This gene"
    n = len(edges)
    grounded = sum(1 for e in edges if e["grounded"])
    parts: list[str] = []
    citations: list[str] = []

    score = target.get("rank_score")
    if score is not None:
        parts.append(f"{label} scores {score:.2f} as a candidate target.")

    if n:
        parts.append(
            f"{grounded} of {n} evidence edge{'s' if n != 1 else ''} are grounded against "
            "reference databases (CARD/UniProt)."
        )

    # Cite the two strongest edges concretely.
    for e in _sorted_edges(edges)[:2]:
        verb = _RELATION_VERB.get(e["relation"], e["relation"].replace("_", " "))
        tgt = e.get("target") or "its mechanism"
        cid = _citation_id(e)
        clause = f"it {verb} {tgt}"
        if cid:
            clause += f" [{cid}]"
            citations.append(cid)
        parts.append(clause + ".")

    comps = target.get("score_components") or {}
    fs = comps.get("flipper_support") or 0
    if fs:
        parts.append(
            f"It reverses across the lineage (flipper support {fs}) — a collateral-"
            "sensitivity signal that motivates cycling."
        )

    tract = target.get("tractability") or {}
    if tract.get("assessed"):
        if not tract.get("has_target"):
            parts.append(
                "ChEMBL records no known chemical matter for its UniProt accession — "
                "a novel, unexploited target."
            )
            if tract.get("queried_acc"):
                citations.append(f"ChEMBL:{tract['queried_acc']}")
        elif tract.get("chembl_target_id"):
            bits = []
            if tract.get("n_bioactivities"):
                bits.append(f"{tract['n_bioactivities']} bioactivities")
            if tract.get("mechanisms"):
                bits.append(f"{len(tract['mechanisms'])} known-drug mechanism(s)")
            detail = ", ".join(bits) or "recorded activity"
            parts.append(f"ChEMBL {tract['chembl_target_id']} has {detail} — precedented chemistry.")
            citations.append(f"ChEMBL:{tract['chembl_target_id']}")

    # De-duplicate citations, preserve order.
    seen: set[str] = set()
    uniq = [c for c in citations if not (c in seen or seen.add(c))]
    return " ".join(parts), uniq


def shape_target(
    target_row: dict,
    edge_rows: list[dict],
    strain_flags: dict | None = None,
) -> dict:
    """Shape one target row (+ its edges) into the API/UI view. Pure."""
    meta = target_row.get("metadata") or {}
    locus = target_row.get("locus_tag") or meta.get("locus_tag")
    wp = target_row.get("wp") or meta.get("wp")
    edges = [shape_evidence_edge(r) for r in edge_rows]
    edges = _sorted_edges(edges)
    grounded = sum(1 for e in edges if e["grounded"])

    view = {
        "id": str(target_row["id"]) if target_row.get("id") else None,
        "gene_id": str(target_row["gene_id"]) if target_row.get("gene_id") else None,
        "locus_tag": locus,
        "name": target_row.get("name") or meta.get("name"),
        "product": target_row.get("product") or meta.get("product"),
        "mechanism": target_row.get("mechanism"),
        "rank_score": (float(target_row["rank_score"]) if target_row.get("rank_score") is not None else None),
        "score_components": meta.get("score_components") or {},
        "tractability": target_row.get("tractability") or {},
        "evidence": edges[:_MAX_EVIDENCE],
        "evidence_counts": {"total": len(edges), "grounded": grounded},
        "structure": {"locus_tag": locus, "wp": wp, "available": bool(wp)},
        "in_strain": bool((strain_flags or {}).get("in_strain")),
        "strain_flipper": bool((strain_flags or {}).get("strain_flipper")),
    }
    rationale, citations = deterministic_rationale(
        {
            "locus_tag": locus,
            "name": view["name"],
            "rank_score": view["rank_score"],
            "score_components": view["score_components"],
            "tractability": view["tractability"],
        },
        edges,
    )
    view["rationale"] = rationale
    view["rationale_citations"] = citations
    view["rationale_source"] = "deterministic"
    return view


def shape_targets(
    strain: dict | None,
    organism: str,
    target_rows: list[dict],
    edges_by_gene: dict[str, list[dict]],
    strain_flags_by_gene: dict[str, dict] | None = None,
) -> dict:
    """Assemble the full /api/targets payload. Pure; edges/flags keyed by gene id str."""
    flags = strain_flags_by_gene or {}
    targets = []
    for row in target_rows:
        gid = str(row.get("gene_id"))
        targets.append(shape_target(row, edges_by_gene.get(gid, []), flags.get(gid)))
    targets.sort(key=lambda t: (t["rank_score"] is None, -(t["rank_score"] or 0.0), t.get("locus_tag") or ""))
    return {
        "strain": strain,
        "organism": organism,
        "targets": targets,
        "counts": {"targets": len(targets), "with_structure": sum(1 for t in targets if t["structure"]["available"])},
    }


def apply_cached_rationales(payload: dict, cache: dict) -> dict:
    """Replace each target's deterministic rationale with a pre-reviewed cached one
    where the cache has an entry (keyed by locus_tag). Pure and in-place-safe.

    A cached entry must carry a ``narrative``; its ``citations`` (if present) replace
    the deterministic citations so the served text stays auditable. Targets without a
    cache entry keep their deterministic rationale untouched — never fabricated. The
    ``rationale_source`` flips to ``"cached"`` so the UI can label it honestly.
    """
    if not cache:
        return payload
    for t in payload.get("targets", []):
        entry = cache.get(t.get("locus_tag"))
        if isinstance(entry, dict) and entry.get("narrative"):
            t["rationale"] = entry["narrative"]
            if entry.get("citations"):
                t["rationale_citations"] = list(entry["citations"])
            t["rationale_source"] = "cached"
            t["rationale_model"] = entry.get("model")
    return payload
