"""BurkData adapter — the real Burkholderia multivorans experimental-evolution record.

This is the dataset the whole product is built to explain: 47 lab isolates evolved
along 11 lineages, with per-gene indel calls (gene-gain/loss "flippers"), reference
gene annotations, and per-lineage antibiotic resistance/sensitivity. It supersedes
the PubMLST reconstruction — here the lineage is *real* (the experimental design),
not inferred.

This module only reads local files (no network, no LLM). The heavy per-strain
flipper marking stays in the deterministic `ingestion/` core; here we parse and
select. `make_burk_snapshot.py` serializes the output to a committed snapshot so the
demo seeds offline.
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import yaml

ORGANISM = "Burkholderia multivorans"


def burkdata_dir() -> Path:
    """Locate the BurkData tree (env override, else sibling of the repo)."""
    env = os.environ.get("BURKDATA_DIR")
    if env:
        return Path(env)
    # backend/app/sources/burkdata.py -> parents[4] == AchillesScience (repo parent)
    return Path(__file__).resolve().parents[4] / "BurkData"


def _lineage_paths(root: Path) -> dict[str, list[str]]:
    data = yaml.safe_load((root / "IndelFlip/pipeline/lineage_paths.yaml").read_text())
    return {k: [str(s) for s in v] for k, v in data.items() if re.fullmatch(r"L\d+", k)}


def _gene_products(root: Path) -> dict[str, dict]:
    """locus_tag -> {product, wp, gene_symbol} from the parsed GFF (gene_position.csv)."""
    out: dict[str, dict] = {}
    path = root / "IndelFlip/data/metadata/gene_position.csv"
    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 9 or row[2] != "CDS":
                continue
            attrs = row[8]
            m_locus = re.search(r"locus_tag=([^;]+)", attrs)
            if not m_locus:
                continue
            m_prod = re.search(r"product=([^;]+)", attrs)
            m_wp = re.search(r"protein_id=([^;,\"]+)", attrs)
            m_gene = re.search(r"gene=([^;]+)", attrs)
            info = {
                "product": m_prod.group(1) if m_prod else None,
                "wp": m_wp.group(1) if m_wp else None,
                "gene_symbol": m_gene.group(1) if m_gene else None,
            }
            # gene_by_indels labels some rows by symbol (apbC) rather than locus_tag,
            # so index by both so the product join always resolves.
            out[m_locus.group(1)] = info
            if m_gene and m_gene.group(1) not in out:
                out[m_gene.group(1)] = info
    return out


def _res_sens(root: Path) -> dict[str, dict]:
    """founder strain id -> {sensitivity: [...drugs], resistance: [...drugs]}."""
    out: dict[str, dict] = {}
    path = root / "IndelFlip/data/metadata/Lineage_Res_Sensy.csv"
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            lineage = (row.get("Lineage") or "").strip()
            if not lineage:
                continue
            rec = out.setdefault(lineage, {"sensitivity": [], "resistance": []})
            sens = (row.get("Sensitivity") or "").strip()
            res = (row.get("Resistance") or "").strip()
            if sens and sens.upper() != "N/A" and sens not in rec["sensitivity"]:
                rec["sensitivity"].append(sens)
            if res and res.upper() != "N/A" and res not in rec["resistance"]:
                rec["resistance"].append(res)
    return out


def load_records(top_flipper_genes: int = 60) -> dict:
    """Parse BurkData into the normalized record set the seed consumes.

    Returns strains, lineage paths, a parent map (real experimental lineage), the
    selected flipper genes with per-strain indel presence, and per-lineage
    resistance/sensitivity. Flipper-gene *selection* (which genes flip at all) is
    done here to bound size; the per-strain is_flipper marking is redone by the
    tested deterministic detector in `ingestion/`.
    """
    root = burkdata_dir()
    lineages = _lineage_paths(root)
    products = _gene_products(root)
    res_sens = _res_sens(root)

    # Indel matrix: chr, genestart, geneend, gene, <47 strain columns>.
    rows = list(csv.reader((root / "IndelFlip/data/gene/gene_by_indels.csv").open()))
    header, body = rows[0], rows[1:]
    strain_ids = header[4:]
    strain_set = set(strain_ids)

    # Real lineage: within each path, each strain's parent is the previous strain
    # that exists in the indel matrix. Founders (path heads) are roots.
    parent: dict[str, str | None] = {}
    strain_lineages: dict[str, list[str]] = {s: [] for s in strain_ids}
    founders: set[str] = set()
    for lname, path in lineages.items():
        present = [s for s in path if s in strain_set]
        for i, s in enumerate(present):
            strain_lineages[s].append(lname)
            if i == 0:
                parent.setdefault(s, None)
                founders.add(s)
            else:
                parent.setdefault(s, present[i - 1])
    for s in strain_ids:
        parent.setdefault(s, None)  # any strain not on a path stands alone

    def present(val: str) -> bool:
        return val.strip() not in ("", "0", "0.0")

    # Score every gene by how much it flips across the real lineages; keep the top N.
    scored: list[dict] = []
    for r in body:
        chrom, gs, ge, gene = r[0], int(r[1]), int(r[2]), r[3]
        deltas = {s: r[4 + i] for i, s in enumerate(strain_ids)}
        pres = {s: present(v) for s, v in deltas.items()}
        support = trans_total = 0
        for path in lineages.values():
            seq = [pres[s] for s in path if s in pres]
            if len(seq) < 3:
                continue
            t = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
            if t >= 2:
                support += 1
                trans_total += t
        if support:
            meta = products.get(gene, {})
            scored.append(
                {
                    "locus_tag": gene,
                    "gene_symbol": meta.get("gene_symbol") or (gene if not gene.startswith("A8H40") else None),
                    "product": meta.get("product"),
                    "wp": meta.get("wp"),
                    "chrom": chrom,
                    "start": gs,
                    "end": ge,
                    "support": support,
                    "transitions": trans_total,
                    "presence": {s: pres[s] for s in strain_ids},
                    "delta": {s: int(deltas[s]) for s in strain_ids if deltas[s].strip() not in ("", ".")},
                }
            )
    scored.sort(key=lambda g: (-g["support"], -g["transitions"], g["start"]))
    genes = scored[:top_flipper_genes]

    return {
        "organism": ORGANISM,
        "strain_ids": strain_ids,
        "lineages": lineages,
        "parent": parent,
        "founders": sorted(founders, key=int),
        "strain_lineages": strain_lineages,
        "genes": genes,
        "res_sens": res_sens,
        "n_flipper_genes_total": sum(1 for _ in scored),
    }
