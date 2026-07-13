"""Domain registry — proves the pipeline is config-driven, not Burkholderia-forked.

Checks: the registry is the single source of truth the seed reads from; the flagship is
seed-ready; the second domain is an honest scaffold (real MLST scheme, NO fabricated
reference genes); and the PubMLST fetch adapter routes by the domain's own db + loci.
"""

from __future__ import annotations

import inspect

from app.ingestion.domains import (
    BURKHOLDERIA,
    PSEUDOMONAS,
    REGISTRY,
    get_domain,
    list_domains,
)


def test_registry_lookup_and_default():
    assert get_domain(None).key == "burkholderia"
    assert get_domain("PSEUDOMONAS").key == "pseudomonas"  # case-insensitive
    import pytest

    with pytest.raises(KeyError):
        get_domain("mycobacterium")


def test_seed_derives_its_constants_from_the_registry():
    # The seed's organism + public reference genes must BE the config, proving the
    # registry actually drives ingestion (not a parallel copy that could drift).
    from app.ingestion import seed

    assert seed.ORGANISM == BURKHOLDERIA.organism
    assert len(seed.PUBLIC_REFERENCE_GENES) == len(BURKHOLDERIA.reference_genes)
    assert seed.PUBLIC_REFERENCE_GENES[0]["locus_tag"] == BURKHOLDERIA.reference_genes[0]["locus_tag"]


def test_flagship_is_ready_and_grounded():
    assert BURKHOLDERIA.has_snapshot is True
    assert BURKHOLDERIA.has_reference_genes is True
    assert BURKHOLDERIA.ready is True
    # Every reference gene carries a real locus tag (no blanks).
    assert all(g.get("locus_tag") for g in BURKHOLDERIA.reference_genes)


def test_second_domain_is_an_honest_scaffold():
    # Real, public config identifiers…
    assert PSEUDOMONAS.organism == "Pseudomonas aeruginosa"
    assert "paeruginosa" in PSEUDOMONAS.pubmlst_isolates_db
    assert PSEUDOMONAS.mlst_loci == ("acsA", "aroE", "guaA", "mutL", "nuoD", "ppsA", "trpE")
    # …but NO fabricated grounded data: empty reference catalog, not seed-ready yet.
    assert PSEUDOMONAS.reference_genes == ()
    assert PSEUDOMONAS.ready is False


def test_list_domains_reports_readiness():
    items = {d["key"]: d for d in list_domains()}
    assert items["burkholderia"]["ready"] is True
    assert items["pseudomonas"]["ready"] is False
    assert items["pseudomonas"]["reference_genes"] == 0


def test_fetch_adapter_routes_by_domain():
    # The fetch path is parameterized by the domain's db + loci (not hard-coded).
    from app.sources import pubmlst

    sig = inspect.signature(pubmlst.fetch_isolates)
    assert "isolates_db" in sig.parameters and "loci" in sig.parameters
    assert hasattr(pubmlst, "fetch_domain_isolates")


def test_corpus_spec_is_domain_driven_and_never_fabricated():
    from app.ingestion.domains import DomainConfig
    from app.sources.make_literature_snapshot import CORPUS, _corpus_for_domain

    # Burkholderia keeps its hand-tuned corpus verbatim (byte-identical reproducibility).
    assert _corpus_for_domain(BURKHOLDERIA) is CORPUS
    # A scaffold with no reference genes yields NO corpus — never invents one.
    assert _corpus_for_domain(PSEUDOMONAS) == []
    # A domain WITH real reference genes yields a valid per-gene harvest spec.
    d = DomainConfig(
        key="x", organism="Testium example", pubmlst_isolates_db="u", mlst_loci=("a",),
        reference_genes=({"locus_tag": "L1", "name": "MexR", "product": "regulator"},),
        europepmc_query="Testium resistance efflux",
    )
    spec = _corpus_for_domain(d)
    assert len(spec) == 1
    assert spec[0]["locus"] == "L1" and spec[0]["symbol"] == "MexR" and spec[0]["queries"]
