"""Bring-your-own-strains: deterministic ingestion of an uploaded genotype table
into a lineage graph with flipper detection.

Runs the SAME deterministic core as the seeded demo (MST lineage over allelic
distance + allele-reversal flipper detection) on a caller's CSV — no DB write, no
LLM, no network. A stateless preview so a researcher can drop in their own isolates
and immediately see the reversible-target structure.

Accepted CSV: one row per isolate; an id column (id/isolate/strain/sample/name, else
the first column); every other non-metadata column is treated as a locus/feature
(MLST allele numbers, gene presence/absence, SNP calls — anything categorical).
Optional metadata columns (year, country, st, source, date, region) are recognized
and excluded from the genotype.
"""

from __future__ import annotations

import io
from uuid import NAMESPACE_URL, UUID, uuid5

import polars as pl

from app.ingestion.flippers import build_lineage_paths, detect_mlst_flippers
from app.ingestion.lineage import build_mst_lineage

_ID_ALIASES = {"id", "isolate", "strain", "sample", "name", "genome", "accession"}
_META_COLS = {
    "year", "country", "st", "sequence_type", "source", "date", "collection_date",
    "region", "continent", "host", "clade", "lineage", "notes",
}

# Guardrails so a pasted spreadsheet can't DoS the deterministic core.
MAX_STRAINS = 500
MAX_LOCI = 400
MIN_STRAINS = 3


class UploadError(ValueError):
    """Raised for malformed / out-of-bounds uploads; surfaced to the client as 400."""


def _strain_uuid(external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"achilles/upload/strain/{external_id}")


def parse_profiles(content: bytes | str) -> tuple[list[dict], list[str], dict]:
    """Parse CSV bytes/text → (records, loci, warnings).

    records: [{id, profile:{locus: int_code}, year?}] with alleles integer-coded per
    locus (a stable value→index map) so distance + flipper math is numeric.
    """
    raw = content.encode() if isinstance(content, str) else content
    try:
        df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0)  # all-string, we coerce
    except Exception as exc:  # noqa: BLE001
        raise UploadError(f"could not parse CSV: {exc}") from exc

    if df.height == 0 or df.width < 2:
        raise UploadError("CSV needs a header row, an id column, and ≥1 genotype column.")

    cols = df.columns
    lower = {c: c.strip().lower() for c in cols}
    id_col = next((c for c in cols if lower[c] in _ID_ALIASES), cols[0])
    locus_cols = [c for c in cols if c != id_col and lower[c] not in _META_COLS]
    if not locus_cols:
        raise UploadError("no genotype columns found (only id/metadata columns present).")
    if len(locus_cols) > MAX_LOCI:
        raise UploadError(f"too many genotype columns ({len(locus_cols)} > {MAX_LOCI}).")

    year_col = next((c for c in cols if lower[c] == "year"), None)

    # Integer-code each locus's distinct values (deterministic: sorted).
    codings: dict[str, dict[str, int]] = {}
    for c in locus_cols:
        vals = sorted({v for v in df[c].to_list() if v not in (None, "")})
        codings[c] = {v: i + 1 for i, v in enumerate(vals)}

    records: list[dict] = []
    seen: set[str] = set()
    for row in df.iter_rows(named=True):
        ext = str(row[id_col]).strip()
        if not ext or ext in seen:
            continue  # skip blank/duplicate ids deterministically (first wins)
        seen.add(ext)
        profile = {
            c: codings[c][row[c]]
            for c in locus_cols
            if row[c] not in (None, "") and row[c] in codings[c]
        }
        if not profile:
            continue
        rec: dict = {"id": ext, "profile": profile}
        if year_col and row.get(year_col) not in (None, ""):
            try:
                rec["year"] = int(str(row[year_col])[:4])
            except (TypeError, ValueError):
                pass
        records.append(rec)

    if len(records) < MIN_STRAINS:
        raise UploadError(
            f"need ≥{MIN_STRAINS} isolates with genotypes to reconstruct a lineage "
            f"(found {len(records)})."
        )
    if len(records) > MAX_STRAINS:
        raise UploadError(f"too many isolates ({len(records)} > {MAX_STRAINS}).")

    warnings: dict = {}
    dropped = df.height - len(records)
    if dropped > 0:
        warnings["dropped_rows"] = dropped
    return records, locus_cols, warnings


def build_upload_graph(content: bytes | str, *, organism: str = "uploaded cohort") -> dict:
    """Parse an uploaded table and return a lineage graph + flipper summary.

    Output mirrors the `/api/graph/lineage` LineageGraph shape (nodes + edges) so the
    frontend LineageTree renders it unchanged, plus a `summary` block.
    """
    records, loci, warnings = parse_profiles(content)

    parent = build_mst_lineage(records, loci=loci)  # {ext_id: ext_parent | None}
    sid = {r["id"]: _strain_uuid(r["id"]) for r in records}
    parent_uuid: dict[UUID, UUID | None] = {
        sid[r["id"]]: (sid[parent[r["id"]]] if parent.get(r["id"]) else None) for r in records
    }
    paths = build_lineage_paths(parent_uuid)

    profiles_by_uuid = {sid[r["id"]]: r["profile"] for r in records}
    flippers = detect_mlst_flippers(profiles_by_uuid, paths, loci=loci)
    flip_count = {u: len(s) for u, s in flippers.items()}

    id_by_uuid = {sid[r["id"]]: r["id"] for r in records}
    nodes = [
        {
            "id": str(u),
            "label": id_by_uuid[u],
            "parent_id": (str(parent_uuid[u]) if parent_uuid[u] else None),
            "flipper_count": flip_count.get(u, 0),
        }
        for u in parent_uuid
    ]
    node_ids = {n["id"] for n in nodes}
    edges = [
        {"source": n["parent_id"], "target": n["id"]}
        for n in nodes
        if n["parent_id"] and n["parent_id"] in node_ids
    ]

    carriers = sum(1 for n in nodes if n["flipper_count"] > 0)
    summary = {
        "organism": organism,
        "strains": len(nodes),
        "loci": len(loci),
        "flipper_carrying": carriers,
        "max_flipper": max((n["flipper_count"] for n in nodes), default=0),
        "roots": sum(1 for n in nodes if not n["parent_id"]),
        "warnings": warnings,
    }
    return {"nodes": nodes, "edges": edges, "summary": summary}
