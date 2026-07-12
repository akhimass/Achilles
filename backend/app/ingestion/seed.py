"""Seed the database with the real, reproducible demo dataset.

Run with `make seed`. Reads the committed BurkData snapshot (the real Burkholderia
multivorans experimental-evolution record: 47 isolates, 11 real lineages, per-gene
indel flippers, gene products, and per-lineage resistance/sensitivity), runs the
deterministic pipeline — build the real lineage, detect flippers along it — and
writes strains, genes, and variants to Postgres via raw SQL matching db/schema.sql.
Idempotent: stable UUIDs + upserts on the schema UNIQUE keys.

An alternate PubMLST/MLST builder (`build_dataset`) is retained and tested; the
demo uses BurkData. No network, no LLM here: `sources/make_burk_snapshot.py`
produces the snapshot; this module only consumes it and computes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from app.ingestion.flippers import LineagePath, build_lineage_paths, detect_flippers, detect_mlst_flippers
from app.ingestion.lineage import MLST_LOCI, annotate_effects, build_mst_lineage
from app.ingestion.parsers import mlst_reference_alleles, mlst_variant_table, parse_variant_table
from app.models.domain import Gene, Strain, Variant, VariantEffect, VariantKind

_DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"
SNAPSHOT = _DEMO / "bmultivorans_pubmlst.json"
SNAPSHOT_BURK = _DEMO / "bmultivorans_burkdata.json"
ORGANISM = "Burkholderia multivorans"

# Replicon offsets so a genome-wide coordinate is unique across the 3 replicons
# (each replicon numbers from 1). Used as `ref_position` for indel variants.
CHROM_OFFSET: dict[str, int] = {
    "NZ_CP020397.1": 0,
    "NZ_CP020398.1": 10_000_000_000,
    "NZ_CP020399.1": 20_000_000_000,
}


# ─── BurkData (real experimental evolution — the demo) ───────────────────────


def _burk_strain_id(external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/strain/burkdata/{external_id}")


def _burk_gene_id(locus_tag: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/gene/{ORGANISM}/{locus_tag}")


def _variant_uuid(strain_id: UUID, kind: str, ref_position: int, alt_allele: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/variant/{strain_id}/{kind}/{ref_position}/{alt_allele}")


def _genome_position(chrom: str, start: int) -> int:
    return CHROM_OFFSET.get(chrom, 30_000_000_000) + int(start)


def build_burk_dataset(records: dict) -> tuple[list[Strain], list[Gene], list[Variant], int]:
    """Deterministic core over the real BurkData record set.

    Returns (strains with real lineage parents, flipper genes, indel variants with
    is_flipper set, number of reverting gene sites). Pure and network-free.
    """
    strain_ids: list[str] = records["strain_ids"]
    lineages: dict[str, list[str]] = records["lineages"]
    genes_raw: list[dict] = records["genes"]
    res_sens: dict[str, dict] = records["res_sens"]
    strain_lineages: dict[str, list[str]] = records["strain_lineages"]
    founders = set(records["founders"])
    parent: dict[str, str | None] = records["parent"]
    strain_set = set(strain_ids)

    sid = {s: _burk_strain_id(s) for s in strain_ids}
    gid = {g["locus_tag"]: _burk_gene_id(g["locus_tag"]) for g in genes_raw}

    # Strains with real experimental-lineage parents.
    strains: list[Strain] = []
    for s in strain_ids:
        p = parent.get(s)
        meta: dict = {
            "lineages": strain_lineages.get(s, []),
            "lineage_label": ", ".join(strain_lineages.get(s, [])) or None,
            "founder": s in founders,
        }
        # Persist observed resistance/sensitivity for EVERY strain that has it (not just
        # founders) so the deterministic trajectory retrieval can trace "what real
        # lineages did next" back to specific strains. Local BurkData only; the public
        # path has no such record, so the trajectory beat shows its honest empty state.
        if s in res_sens:
            meta["resistance"] = res_sens[s].get("resistance", [])
            meta["sensitivity"] = res_sens[s].get("sensitivity", [])
        strains.append(
            Strain(
                id=sid[s],
                external_id=s,
                source="burkdata",
                organism=ORGANISM,
                label=s,
                parent_id=sid[p] if p else None,
                metadata=meta,
            )
        )

    # Flipper genes (with real products).
    genes: list[Gene] = [
        Gene(
            id=gid[g["locus_tag"]],
            locus_tag=g["locus_tag"],
            name=g.get("gene_symbol"),
            product=g.get("product"),
            organism=ORGANISM,
            metadata={
                "chrom": g["chrom"],
                "start": g["start"],
                "end": g["end"],
                "flipper_support": g["support"],
                "wp": g.get("wp"),
            },
        )
        for g in genes_raw
    ]

    # Real lineage paths, then flipper detection over indel presence/absence.
    paths: list[LineagePath] = [
        LineagePath([sid[s] for s in path if s in strain_set]) for path in lineages.values()
    ]
    detection: dict[UUID, list[Variant]] = {sid[s]: [] for s in strain_ids}
    for g in genes_raw:
        pos = _genome_position(g["chrom"], g["start"])
        for s in strain_ids:
            present = bool(g["presence"].get(s, False))
            detection[sid[s]].append(
                Variant(
                    strain_id=sid[s],
                    kind=VariantKind.indel,
                    ref_position=pos,
                    allele_freq=1.0 if present else 0.0,
                )
            )
    sites = detect_flippers(detection, paths, min_allele_freq=0.5)
    flipping_at: dict[int, set[UUID]] = {s.ref_position: set(s.strain_ids) for s in sites}

    # Persisted variants: real indels (present only), is_flipper where the gene
    # reverts along a lineage running through the strain.
    variants: list[Variant] = []
    for g in genes_raw:
        pos = _genome_position(g["chrom"], g["start"])
        flippers = flipping_at.get(pos, set())
        for s in strain_ids:
            if not g["presence"].get(s, False):
                continue
            delta = int(g["delta"].get(s, 0))
            effect = VariantEffect.frameshift if delta % 3 != 0 else None
            variants.append(
                Variant(
                    strain_id=sid[s],
                    kind=VariantKind.indel,
                    ref_position=pos,
                    ref_allele="0",
                    alt_allele=str(delta),
                    gene_id=gid[g["locus_tag"]],
                    effect=effect,
                    allele_freq=1.0,
                    is_flipper=sid[s] in flippers,
                    metadata={
                        "locus_tag": g["locus_tag"],
                        "product": g.get("product"),
                        "gene_symbol": g.get("gene_symbol"),
                        "chrom": g["chrom"],
                        "gene_start": g["start"],
                        "indel_delta": delta,
                        "flipper_support": g["support"],
                    },
                )
            )

    return strains, genes, variants, len(flipping_at)


# ─── MLST / PubMLST (alternate source — retained and tested) ─────────────────

LOCUS_GENES: dict[str, tuple[str, str]] = {
    "atpD": ("atpD", "ATP synthase F1 subunit beta"),
    "gltB": ("gltB", "glutamate synthase large subunit"),
    "gyrB": ("gyrB", "DNA gyrase subunit B"),
    "lepA": ("lepA", "elongation factor 4 (translation GTPase)"),
    "phaC": ("phaC", "polyhydroxyalkanoate synthase subunit PhaC"),
    "recA": ("recA", "recombinase A"),
    "trpB": ("trpB", "tryptophan synthase subunit beta"),
}

# Public resistance-gene catalog (identities from the NCBI B. multivorans reference
# genome GCF_001718455 / NZ_CP020397-9 — all public annotation). These are the gene
# families the committed literature corpus is keyed to, seeded so the evidence graph
# and structure viewer work in the public demo even without the private BurkData
# snapshot. Gene id uses `_burk_gene_id(locus)` to match the corpus edges' source.
PUBLIC_REFERENCE_GENES: list[dict] = [
    {"locus_tag": "A8H40_RS07590", "name": "MarR", "wp": "WP_006410546.1",
     "product": "MarR family winged helix-turn-helix transcriptional regulator"},
    {"locus_tag": "A8H40_RS24275", "name": "AraC/MarA-family activator", "wp": None,
     "product": "AraC family transcriptional regulator"},
    {"locus_tag": "A8H40_RS17945", "name": "LysR-family regulator", "wp": None,
     "product": "LysR family transcriptional regulator"},
    {"locus_tag": "A8H40_RS19975", "name": "drug/efflux transporter", "wp": None,
     "product": "DMT family transporter"},
    {"locus_tag": "A8H40_RS00780", "name": "two-component response regulator", "wp": "WP_006409650.1",
     "product": "response regulator"},
]


def reference_genes() -> list[Gene]:
    return [
        Gene(
            id=_burk_gene_id(g["locus_tag"]),
            locus_tag=g["locus_tag"],
            name=g["name"],
            product=g["product"],
            organism=ORGANISM,
            metadata={"wp": g["wp"], "source": "reference-annotation"},
        )
        for g in PUBLIC_REFERENCE_GENES
    ]


def mlst_genes() -> list[Gene]:
    return [
        Gene(id=_gene_id(locus), locus_tag=locus, name=sym, product=prod, organism=ORGANISM)
        for locus, (sym, prod) in LOCUS_GENES.items()
    ]


def _strain_id(external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/strain/pubmlst/{external_id}")


def _gene_id(locus: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/gene/{ORGANISM}/{locus}")


def build_dataset(records: list[dict]) -> tuple[list[Strain], list[Variant], int]:
    """Deterministic MLST core (PubMLST): records -> (strains, variants, flipper count)."""
    ext_ids = {r["id"] for r in records}
    ref_alleles = mlst_reference_alleles([r["profile"] for r in records])
    gene_by_locus = {locus: _gene_id(locus) for locus in MLST_LOCI}

    strains: dict = {}
    for r in records:
        ext = str(r["id"])
        strains[r["id"]] = Strain(
            id=_strain_id(ext),
            external_id=ext,
            source="pubmlst",
            organism=ORGANISM,
            label=r.get("isolate") or f"isolate {ext}",
            metadata={
                "st": r.get("st"),
                "year": r.get("year"),
                "country": r.get("country"),
                "continent": r.get("continent"),
                "isolation_source": r.get("source"),
                "isolation_detail": r.get("detail"),
                "ncbi_assembly": r.get("ncbi"),
                "pmids": r.get("pmids", []),
                "mlst_profile": r["profile"],
            },
        )

    parent_of_ext = build_mst_lineage(records)
    for ext_id, parent_ext in parent_of_ext.items():
        strains[ext_id].parent_id = None if parent_ext is None else _strain_id(str(parent_ext))

    parent_uuid: dict[UUID, UUID | None] = {s.id: s.parent_id for s in strains.values()}
    paths = build_lineage_paths(parent_uuid)
    profiles_by_strain = {strains[e].id: strains[e].metadata["mlst_profile"] for e in ext_ids}
    flippers_by_strain = detect_mlst_flippers(profiles_by_strain, paths)
    all_sites = {pair for sites in flippers_by_strain.values() for pair in sites}

    variants: list[Variant] = []
    for r in records:
        strain = strains[r["id"]]
        strain_flips = flippers_by_strain.get(strain.id, set())
        table = mlst_variant_table(r["profile"], ref_alleles)
        vs = parse_variant_table(table, strain.id)
        vs = annotate_effects(vs, gene_by_locus)
        for v in vs:
            v.is_flipper = (v.metadata.get("locus"), v.metadata.get("allele")) in strain_flips
        variants.extend(vs)

    return list(strains.values()), variants, len(all_sites)


# ─── Persistence ─────────────────────────────────────────────────────────────


async def _persist(strains: list[Strain], genes: list[Gene], variants: list[Variant]) -> None:
    # DB imports are local so the deterministic core imports without a driver.
    from sqlalchemy import text

    from app.db import SessionLocal

    parent_rows = [
        {"id": str(s.id), "parent_id": str(s.parent_id)} for s in strains if s.parent_id is not None
    ]
    async with SessionLocal() as session:
        async with session.begin():
            if genes:
                await session.execute(
                    text(
                        """
                        INSERT INTO genes (id, locus_tag, name, product, organism, metadata)
                        VALUES (:id, :locus_tag, :name, :product, :organism, CAST(:metadata AS jsonb))
                        ON CONFLICT (organism, locus_tag) DO UPDATE
                          SET name = EXCLUDED.name, product = EXCLUDED.product,
                              metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "id": str(g.id),
                            "locus_tag": g.locus_tag,
                            "name": g.name,
                            "product": g.product,
                            "organism": g.organism,
                            "metadata": json.dumps(g.metadata),
                        }
                        for g in genes
                    ],
                )

            if strains:
                await session.execute(
                    text(
                        """
                        INSERT INTO strains (id, external_id, source, organism, label, metadata)
                        VALUES (:id, :external_id, :source, :organism, :label, CAST(:metadata AS jsonb))
                        ON CONFLICT (source, external_id) DO UPDATE
                          SET organism = EXCLUDED.organism, label = EXCLUDED.label,
                              metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "id": str(s.id),
                            "external_id": s.external_id,
                            "source": s.source,
                            "organism": s.organism,
                            "label": s.label,
                            "metadata": json.dumps(s.metadata),
                        }
                        for s in strains
                    ],
                )

            if parent_rows:
                await session.execute(
                    text("UPDATE strains SET parent_id = :parent_id WHERE id = :id"), parent_rows
                )

            if variants:
                await session.execute(
                    text(
                        """
                        INSERT INTO variants
                          (id, strain_id, kind, ref_position, ref_allele, alt_allele,
                           gene_id, effect, allele_freq, is_flipper, metadata)
                        VALUES
                          (:id, :strain_id, :kind, :ref_position, :ref_allele, :alt_allele,
                           :gene_id, :effect, :allele_freq, :is_flipper, CAST(:metadata AS jsonb))
                        ON CONFLICT (strain_id, kind, ref_position, alt_allele) DO UPDATE
                          SET ref_allele = EXCLUDED.ref_allele, gene_id = EXCLUDED.gene_id,
                              effect = EXCLUDED.effect, allele_freq = EXCLUDED.allele_freq,
                              is_flipper = EXCLUDED.is_flipper, metadata = EXCLUDED.metadata
                        """
                    ),
                    [
                        {
                            "id": str(_variant_uuid(v.strain_id, v.kind.value, v.ref_position, v.alt_allele or "")),
                            "strain_id": str(v.strain_id),
                            "kind": v.kind.value,
                            "ref_position": v.ref_position,
                            "ref_allele": v.ref_allele,
                            "alt_allele": v.alt_allele,
                            "gene_id": str(v.gene_id) if v.gene_id else None,
                            "effect": v.effect.value if v.effect else None,
                            "allele_freq": v.allele_freq,
                            "is_flipper": v.is_flipper,
                            "metadata": json.dumps(v.metadata),
                        }
                        for v in variants
                    ],
                )


async def _seed_burkdata() -> None:
    """Local rich demo: the real (private) experimental-evolution record."""
    records = json.loads(SNAPSHOT_BURK.read_text())
    strains, genes, variants, n_sites = build_burk_dataset(records)
    await _persist(strains, genes, variants)
    n_flip = sum(1 for v in variants if v.is_flipper)
    print(
        f"seed: {len(strains)} strains, {len(genes)} flipper genes, "
        f"{len(variants)} indel variants, {n_sites} reverting gene sites "
        f"({n_flip} flipper variant calls) — {ORGANISM} (BurkData, local)"
    )


async def _seed_public() -> None:
    """Public demo (no private snapshot): PubMLST lineage + reference-gene catalog.

    Seeds a real Burkholderia lineage from public PubMLST data plus the public
    resistance-gene families the committed literature corpus is keyed to, so the
    evidence graph and structure viewer work end-to-end on public data alone.
    """
    if not SNAPSHOT.exists():
        raise FileNotFoundError(f"no demo snapshot found ({SNAPSHOT_BURK} or {SNAPSHOT})")
    records = json.loads(SNAPSHOT.read_text())["records"]
    strains, variants, n_sites = build_dataset(records)
    await _persist(strains, mlst_genes() + reference_genes(), variants)
    print(
        f"seed: {len(strains)} strains (PubMLST), {len(variants)} MLST variants, "
        f"{n_sites} flipper sites + {len(PUBLIC_REFERENCE_GENES)} reference genes "
        f"— {ORGANISM} (public)"
    )


async def main(public_only: bool = False) -> None:
    # Prefer the local BurkData snapshot (private, gitignored); otherwise fall back
    # to the fully public demo so a fresh clone still seeds a working graph.
    #
    # `public_only` forces the PUBLIC (PubMLST + committed public caches) path even if
    # a BurkData snapshot is present — this is what the DEPLOYED database is seeded
    # with, guaranteeing no private data can reach a public deployment. On this path
    # collateral_sensitivity comes out empty (it derives from private BurkData), so the
    # cycling panel honestly shows its empty state rather than being backfilled.
    if public_only:
        print("seed: PUBLIC-only path (deploy/reproduction mode) — BurkData ignored")
        await _seed_public()
    elif SNAPSHOT_BURK.exists():
        await _seed_burkdata()
    else:
        await _seed_public()

    # Phase 2: literature -> grounded evidence edges (offline, from committed corpus).
    from app.ingestion.seed_literature import seed_literature

    seeded_edges = False
    try:
        await seed_literature()
        seeded_edges = True
    except FileNotFoundError as exc:
        print(f"seed(literature): skipped — {exc}")

    # Phase 3: promote evidence-supported genes into ranked targets (deterministic
    # rank_score + ChEMBL tractability from the committed cache). Needs the edges.
    if seeded_edges:
        from app.ingestion.seed_targets import seed_targets

        await seed_targets(ORGANISM)

    # Phase 4: collateral-sensitivity pairs from the per-lineage resistance/sensitivity
    # record (deterministic; BurkData-local, gracefully empty on the public path).
    from app.ingestion.seed_collateral import seed_collateral

    await seed_collateral(ORGANISM)


if __name__ == "__main__":
    # `python -m app.ingestion.seed --public` (or ACHILLES_SEED_PUBLIC=1) forces the
    # public reproduction path — used to seed the deployed database.
    _public = "--public" in sys.argv or os.getenv("ACHILLES_SEED_PUBLIC", "").lower() in (
        "1",
        "true",
        "yes",
    )
    asyncio.run(main(public_only=_public))
