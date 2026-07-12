"""Export the PUBLIC demo seed as a self-contained SQL bundle.

Runs the deterministic public builders (PubMLST lineage + reference genes + the
committed literature corpus + ranked targets) and emits idempotent SQL INSERTs that
load any Postgres — including a managed one (Supabase) that a sandbox can't reach over
the wire. This is the "seed without a live asyncpg connection" path, and it keeps the
reproducibility promise: same public inputs → same SQL → same graph.

DATA RIGHTS: PUBLIC ONLY. BurkData is never read here, so nothing private can reach a
committed bundle or a cloud database. Collateral-sensitivity is empty on the public
path (it derives from BurkData), so the cycling panel shows its honest empty state.

    python -m app.ingestion.export_seed_sql > /tmp/achilles_public_seed.sql
    psql "$SUPABASE_DATABASE_URL" -f db/schema.sql -f /tmp/achilles_public_seed.sql
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from app.ingestion.seed import (
    SNAPSHOT,
    build_dataset,
    mlst_genes,
    reference_genes,
    _burk_gene_id,
)
from app.ingestion.seed_literature import load_corpus, rebuild_edges
from app.ingestion.seed_targets import build_targets


# ─── SQL literal helpers ─────────────────────────────────────────────────────


def _lit(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (dict, list)):
        return _lit(json.dumps(v)) + "::jsonb"
    return "'" + str(v).replace("'", "''") + "'"


def _text_array(items: list[str]) -> str:
    if not items:
        return "'{}'::text[]"
    inner = ",".join('"' + str(i).replace('"', '\\"') + '"' for i in items)
    return _lit("{" + inner + "}") + "::text[]"


def _row(vals: list[str]) -> str:
    return "(" + ", ".join(vals) + ")"


def _insert(table: str, cols: list[str], rows: list[list[str]], conflict: str, update: list[str]) -> str:
    if not rows:
        return f"-- {table}: no rows\n"
    head = f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n"
    body = ",\n".join("  " + _row(r) for r in rows)
    sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in update)
    tail = f"\nON CONFLICT ({conflict}) DO UPDATE SET {sets};\n"
    return head + body + tail


# ─── Build the public dataset (no DB, no BurkData) ───────────────────────────


def build_sql() -> str:
    if not SNAPSHOT.exists():
        raise FileNotFoundError(f"public PubMLST snapshot missing: {SNAPSHOT}")

    genes = mlst_genes() + reference_genes()
    records = json.loads(SNAPSHOT.read_text())["records"]
    strains, variants, _ = build_dataset(records)

    corpus = load_corpus()
    papers = [p for p in corpus.get("papers", []) if p.get("pmid")]
    known_pmids = {p["pmid"] for p in papers}
    edges = [e for e in rebuild_edges(corpus) if e.provenance_pmid in known_pmids]

    # Targets from the corpus edges (public path): aggregate per gene, flipper_support 0.
    gene_by_id = {str(g.id): g for g in genes}
    agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "conf": 0.0, "grounded": 0})
    for e in edges:
        a = agg[str(e.source_id)]
        a["n"] += 1
        a["conf"] += e.confidence
        a["grounded"] += 1 if e.grounded else 0
    target_rows = []
    for gid, a in agg.items():
        g = gene_by_id.get(gid)
        if not g:
            continue
        target_rows.append({
            "gene_id": gid, "locus_tag": g.locus_tag, "name": g.name, "product": g.product,
            "wp": (g.metadata or {}).get("wp"),
            "flipper_support": int((g.metadata or {}).get("flipper_support") or 0),
            "n_edges": a["n"], "mean_confidence": a["conf"] / a["n"], "grounded_edges": a["grounded"],
        })
    targets = build_targets(target_rows)

    out: list[str] = [
        "-- Achilles PUBLIC seed (PubMLST + committed caches). Idempotent. No BurkData.",
        "-- Apply after db/schema.sql.",
        "BEGIN;",
    ]

    # genes
    out.append(_insert(
        "genes", ["id", "locus_tag", "name", "product", "organism", "metadata"],
        [[_lit(str(g.id)), _lit(g.locus_tag), _lit(g.name), _lit(g.product), _lit(g.organism),
          _lit(g.metadata)] for g in genes],
        "organism, locus_tag", ["name", "product", "metadata"],
    ))

    # strains (parent_id set in a second pass so referenced rows exist first)
    out.append(_insert(
        "strains", ["id", "external_id", "source", "organism", "label", "metadata"],
        [[_lit(str(s.id)), _lit(s.external_id), _lit(s.source), _lit(s.organism), _lit(s.label),
          _lit(s.metadata)] for s in strains],
        "source, external_id", ["organism", "label", "metadata"],
    ))
    parent_updates = [
        f"UPDATE strains SET parent_id = {_lit(str(s.parent_id))} WHERE id = {_lit(str(s.id))};"
        for s in strains if s.parent_id is not None
    ]
    out.extend(parent_updates)

    # variants
    from app.ingestion.seed import _variant_uuid
    out.append(_insert(
        "variants",
        ["id", "strain_id", "kind", "ref_position", "ref_allele", "alt_allele", "gene_id",
         "effect", "allele_freq", "is_flipper", "metadata"],
        [[_lit(str(_variant_uuid(v.strain_id, v.kind.value, v.ref_position, v.alt_allele or ""))),
          _lit(str(v.strain_id)), _lit(v.kind.value), _lit(v.ref_position), _lit(v.ref_allele),
          _lit(v.alt_allele), _lit(str(v.gene_id) if v.gene_id else None),
          _lit(v.effect.value if v.effect else None), _lit(v.allele_freq), _lit(v.is_flipper),
          _lit(v.metadata)] for v in variants],
        "strain_id, kind, ref_position, alt_allele",
        ["ref_allele", "gene_id", "effect", "allele_freq", "is_flipper", "metadata"],
    ))

    # papers
    from uuid import NAMESPACE_URL, uuid5
    out.append(_insert(
        "papers", ["id", "pmid", "doi", "title", "abstract", "year", "source", "metadata"],
        [[_lit(str(uuid5(NAMESPACE_URL, f"achilles/paper/{p['pmid']}"))), _lit(p["pmid"]),
          _lit(p.get("doi")), _lit(p["title"]), _lit(p.get("abstract")), _lit(p.get("year")),
          _lit(p.get("source", "europepmc")), _lit(p.get("metadata", {}))] for p in papers],
        "pmid", ["title", "abstract", "doi", "year", "metadata"],
    ))

    # evidence_edges
    from app.ingestion.seed_literature import _edge_id
    out.append(_insert(
        "evidence_edges",
        ["id", "source_type", "source_id", "relation", "target_type", "target_id",
         "target_literal", "provenance_pmid", "provenance_db", "provenance_acc", "confidence",
         "extracted_by", "grounded", "metadata"],
        [[_lit(str(_edge_id(e))), _lit(e.source_type.value), _lit(str(e.source_id)),
          _lit(e.relation.value), _lit(e.target_type.value),
          _lit(str(e.target_id) if e.target_id else None), _lit(e.target_literal),
          _lit(e.provenance_pmid), _lit(e.provenance_db), _lit(e.provenance_acc),
          _lit(e.confidence), _lit(e.extracted_by), _lit(e.grounded), _lit(e.metadata)]
         for e in edges],
        "id", ["confidence", "grounded", "provenance_db", "provenance_acc", "metadata"],
    ))

    # targets
    out.append(_insert(
        "targets", ["id", "gene_id", "mechanism", "tractability", "pdb_ids", "rank_score", "metadata"],
        [[_lit(str(t.id)), _lit(str(t.gene_id)), _lit(t.mechanism), _lit(t.tractability),
          _text_array(t.pdb_ids), _lit(t.rank_score), _lit(t.metadata)] for t in targets],
        "id", ["mechanism", "tractability", "pdb_ids", "rank_score", "metadata"],
    ))

    # collateral_sensitivity — PUBLIC, cited reciprocal CS pairs (redistributable), so
    # the cycling beat renders on the public deploy WITH provenance (never blank).
    from app.ingestion.seed_collateral import load_public_cs_pairs
    cs_pairs = load_public_cs_pairs()
    if cs_pairs:
        out.append(_insert(
            "collateral_sensitivity",
            ["organism", "drug_a", "drug_b", "reciprocal", "strength", "n_lineages", "metadata"],
            [[_lit(p.organism), _lit(p.drug_a), _lit(p.drug_b), _lit(p.reciprocal),
              _lit(p.strength), _lit(p.n_lineages), _lit(p.metadata)] for p in cs_pairs],
            "organism, drug_a, drug_b",
            ["reciprocal", "strength", "n_lineages", "metadata"],
        ))

    out.append("COMMIT;")
    counts = (
        f"-- counts: {len(genes)} genes, {len(strains)} strains, {len(variants)} variants, "
        f"{len(papers)} papers, {len(edges)} edges, {len(targets)} targets, "
        f"{len(cs_pairs)} collateral (public/cited)"
    )
    out.append(counts)
    return "\n".join(out) + "\n"


def main() -> None:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    sql = build_sql()
    if dest:
        dest.write_text(sql)
        print(f"wrote {dest} ({sql.count(chr(10))} lines)", file=sys.stderr)
    else:
        sys.stdout.write(sql)


if __name__ == "__main__":
    main()
