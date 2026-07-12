"""Deterministic parsing of variant data into typed `Variant` rows.

No network calls, no LLM — parsing must be reproducible byte-for-byte. Two entry
points: VCF (via cyvcf2) and a normalized tabular form (via polars) for data that
already arrived as SNP/indel matrices.

Phase 1 wires the real representation used by the seeded demo: per-isolate MLST
allele profiles (7 housekeeping loci) from PubMLST. Each locus becomes one SNP-kind
`Variant` whose `alt_allele` is the isolate's allele number and whose `ref_allele`
is the scheme's reference (modal) allele. See `mlst_variant_table`.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import polars as pl

from app.models.domain import Variant, VariantKind

# Canonical MLST loci for the BCC scheme and a stable, non-genomic position per
# locus. `ref_position` on an MLST variant is a scheme locus index (1..7), not a
# genomic coordinate — recorded in metadata as encoding='mlst_allele'.
MLST_LOCI: tuple[str, ...] = ("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB")
MLST_LOCUS_POSITIONS: dict[str, int] = {locus: i + 1 for i, locus in enumerate(MLST_LOCI)}

# Columns that map to first-class Variant fields; anything else rides in metadata.
_TABLE_FIELDS = {"kind", "ref_position", "ref_allele", "alt_allele", "allele_freq"}


def parse_vcf(path: str | Path, strain_id: UUID) -> list[Variant]:
    """Parse a VCF into Variant rows for one strain.

    Kept import-local so the package imports even where cyvcf2's native deps are
    absent (e.g. a frontend-only CI job).
    """
    from cyvcf2 import VCF  # noqa: PLC0415

    variants: list[Variant] = []
    for rec in VCF(str(path)):
        for alt in rec.ALT:
            kind = VariantKind.snp if len(rec.REF) == len(alt) == 1 else VariantKind.indel
            variants.append(
                Variant(
                    strain_id=strain_id,
                    kind=kind,
                    ref_position=int(rec.POS),
                    ref_allele=rec.REF,
                    alt_allele=alt,
                    allele_freq=_first_af(rec),
                )
            )
    return variants


def parse_variant_table(df: pl.DataFrame, strain_id: UUID) -> list[Variant]:
    """Parse a normalized variant table (one row per variant call) for one strain.

    Expected columns (rename upstream to match): kind, ref_position, ref_allele,
    alt_allele, allele_freq. Extra columns are carried into `metadata` (dropping
    nulls so provenance stays clean). Types are coerced so the source can hand us
    ints/floats or their string forms interchangeably.
    """
    required = {"kind", "ref_position"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"variant table missing columns: {sorted(missing)}")

    out: list[Variant] = []
    for row in df.iter_rows(named=True):
        af = row.get("allele_freq")
        ref = row.get("ref_allele")
        alt = row.get("alt_allele")
        out.append(
            Variant(
                strain_id=strain_id,
                kind=VariantKind(row["kind"]),
                ref_position=int(row["ref_position"]),
                ref_allele=None if ref is None else str(ref),
                alt_allele=None if alt is None else str(alt),
                allele_freq=None if af is None else float(af),
                metadata={
                    k: v for k, v in row.items() if k not in _TABLE_FIELDS and v is not None
                },
            )
        )
    return out


def mlst_reference_alleles(profiles: list[dict[str, int]]) -> dict[str, int]:
    """Pick a reference allele per locus: the modal allele across isolates.

    Deterministic — ties break to the smallest allele number. This defines the
    `ref_allele` each isolate's call is compared against.
    """
    ref: dict[str, int] = {}
    for locus in MLST_LOCI:
        counts: dict[int, int] = {}
        for prof in profiles:
            if locus in prof:
                counts[prof[locus]] = counts.get(prof[locus], 0) + 1
        if counts:
            # sort by (-count, allele) so the most common, then smallest, wins
            ref[locus] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return ref


def mlst_variant_table(profile: dict[str, int], ref_alleles: dict[str, int]) -> pl.DataFrame:
    """Build the normalized variant table for one isolate's MLST profile.

    One SNP-kind row per locus; `alt_allele` is the isolate's allele, `ref_allele`
    the scheme reference. `allele_freq` is 1.0 — an MLST allele is a haploid call,
    fully present. `locus`/`allele`/`encoding` ride into metadata via the parser.
    """
    rows = []
    for locus in MLST_LOCI:
        if locus not in profile:
            continue
        rows.append(
            {
                "kind": "snp",
                "ref_position": MLST_LOCUS_POSITIONS[locus],
                "ref_allele": str(ref_alleles.get(locus, "")),
                "alt_allele": str(profile[locus]),
                "allele_freq": 1.0,
                "locus": locus,
                "allele": profile[locus],
                "scheme": "MLST",
                "encoding": "mlst_allele",
            }
        )
    return pl.DataFrame(rows)


def _first_af(rec) -> float | None:
    try:
        af = rec.INFO.get("AF")
        return float(af[0]) if isinstance(af, (list, tuple)) else float(af)
    except (TypeError, ValueError):
        return None
