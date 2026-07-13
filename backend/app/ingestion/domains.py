"""Domain registry — the config that makes the pipeline domain-agnostic.

Achilles is not an "antimicrobial-resistance app"; it is an evidence-graph pipeline that
runs on whatever domain you configure. Everything that used to be hard-coded to
Burkholderia — the organism name, the PubMLST database + MLST scheme, the reference-gene
catalog, the literature query, and which committed data artifacts back the demo — lives
here as a `DomainConfig`. Adding a domain is a config entry plus its (real, fetched) data,
never a code fork.

Honesty rule (same as everywhere else): a domain's reference genes and literature must be
REAL public identifiers, fetched from NCBI/UniProt/Europe PMC — never invented. A domain
with `reference_genes=()` and no committed snapshot is a *scaffold*: its lineage seeds from
real PubMLST data once fetched, and its grounded genes/edges are added when its real
catalog is populated. `ready` reports, honestly, whether a domain can seed offline today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_DEMO = Path(__file__).resolve().parents[3] / "data" / "demo"


@dataclass(frozen=True)
class DomainConfig:
    key: str
    organism: str
    # PubMLST isolates database REST root + the scheme's housekeeping loci (canonical order).
    pubmlst_isolates_db: str
    mlst_loci: tuple[str, ...]
    # Reference resistance/regulator genes: real NCBI locus tags + products (+ RefSeq WP /
    # UniProt accessions). Empty for a scaffold domain until its real catalog is fetched.
    reference_genes: tuple[dict, ...] = ()
    # Europe PMC query used to pull the literature corpus for this domain.
    europepmc_query: str = ""
    # Committed data artifacts (filenames under data/demo/), if any exist yet.
    pubmlst_snapshot: str | None = None
    corpus: str | None = None
    benchmark: str | None = None
    notes: str = ""

    def _artifact(self, name: str | None) -> Path | None:
        return (_DEMO / name) if name else None

    @property
    def snapshot_path(self) -> Path | None:
        return self._artifact(self.pubmlst_snapshot)

    @property
    def has_snapshot(self) -> bool:
        p = self.snapshot_path
        return bool(p and p.exists())

    @property
    def has_reference_genes(self) -> bool:
        return len(self.reference_genes) > 0

    @property
    def ready(self) -> bool:
        """Can this domain seed a real graph offline right now?"""
        return self.has_snapshot and self.has_reference_genes

    def status(self) -> dict:
        return {
            "key": self.key,
            "organism": self.organism,
            "mlst_loci": list(self.mlst_loci),
            "reference_genes": len(self.reference_genes),
            "has_snapshot": self.has_snapshot,
            "has_corpus": bool(self._artifact(self.corpus) and self._artifact(self.corpus).exists()),
            "ready": self.ready,
            "pubmlst_isolates_db": self.pubmlst_isolates_db,
            "notes": self.notes,
        }


# ─── Burkholderia multivorans — the fully-populated flagship domain ──────────
# Values here are AUTHORITATIVE: seed.py derives its organism + reference-gene catalog
# from this config, so the registry is provably what drives ingestion (see test_domains).
BURKHOLDERIA = DomainConfig(
    key="burkholderia",
    organism="Burkholderia multivorans",
    pubmlst_isolates_db="https://rest.pubmlst.org/db/pubmlst_bcc_isolates",
    mlst_loci=("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB"),
    reference_genes=(
        {"locus_tag": "A8H40_RS07590", "name": "MarR", "wp": "WP_006410546.1",
         "product": "MarR family winged helix-turn-helix transcriptional regulator"},
        {"locus_tag": "A8H40_RS24275", "name": "AraC/MarA-family activator", "wp": None,
         "product": "AraC family transcriptional regulator"},
        {"locus_tag": "A8H40_RS17945", "name": "LysR-family regulator", "wp": None,
         "product": "LysR family transcriptional regulator"},
        {"locus_tag": "A8H40_RS19975", "name": "drug/efflux transporter", "wp": None,
         "product": "DMT family transporter"},
        {"locus_tag": "A8H40_RS00780", "name": "two-component response regulator",
         "wp": "WP_006409650.1", "product": "response regulator"},
    ),
    europepmc_query=(
        'Burkholderia multivorans AND (antimicrobial resistance OR efflux OR '
        '"collateral sensitivity" OR MarR OR AcrAB)'
    ),
    pubmlst_snapshot="bmultivorans_pubmlst.json",
    corpus="literature/corpus.json",
    benchmark="benchmark/known_relationships.json",
    notes="Flagship worked example: real PubMLST lineage, grounded literature graph, "
          "cited collateral-sensitivity cycling, and a self-validation benchmark.",
)


# ─── Pseudomonas aeruginosa — a real second domain (scaffold) ────────────────
# The PubMLST database and the classic Curran et al. 2004 7-locus MLST scheme are real,
# public config identifiers. Reference genes are intentionally EMPTY: they must be fetched
# from NCBI/UniProt (see docs/ADDING_A_DOMAIN.md) rather than invented here. Once the
# snapshot + reference catalog are populated, `ready` flips to true and it seeds like
# Burkholderia — no code change.
PSEUDOMONAS = DomainConfig(
    key="pseudomonas",
    organism="Pseudomonas aeruginosa",
    pubmlst_isolates_db="https://rest.pubmlst.org/db/pubmlst_paeruginosa_isolates",
    mlst_loci=("acsA", "aroE", "guaA", "mutL", "nuoD", "ppsA", "trpE"),
    reference_genes=(),  # populate from NCBI/UniProt — never fabricated
    europepmc_query=(
        'Pseudomonas aeruginosa AND (antimicrobial resistance OR efflux OR '
        '"collateral sensitivity" OR MexAB OR MexR)'
    ),
    pubmlst_snapshot="paeruginosa_pubmlst.json",  # not committed yet — fetch to populate
    corpus=None,
    benchmark=None,
    notes="Scaffold: fetch its PubMLST isolates + reference-gene catalog to seed. Lineage "
          "works from real public data; grounded edges follow once its corpus is built.",
)


REGISTRY: dict[str, DomainConfig] = {d.key: d for d in (BURKHOLDERIA, PSEUDOMONAS)}
DEFAULT_DOMAIN = BURKHOLDERIA.key

# Single source of truth for the default organism. Routers derive their organism default
# from here instead of hard-coding the string, so changing the flagship domain (or its
# organism) propagates everywhere and nothing drifts.
DEFAULT_ORGANISM = REGISTRY[DEFAULT_DOMAIN].organism


def get_domain(key: str | None) -> DomainConfig:
    """Look up a domain by key (case-insensitive); defaults to the flagship."""
    if not key:
        return REGISTRY[DEFAULT_DOMAIN]
    d = REGISTRY.get(key.strip().lower())
    if d is None:
        raise KeyError(f"unknown domain '{key}'. Registered: {', '.join(REGISTRY)}")
    return d


def list_domains() -> list[dict]:
    """Registry status for the API / CLI (which domains can seed today)."""
    return [d.status() for d in REGISTRY.values()]
