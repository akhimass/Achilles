"""Generalization proof — the deterministic core is organism-agnostic.

The lineage (MST over allelic distance) and flipper (allele-reversal) detection are the
heart of Achilles. These tests feed them a NON-Burkholderia genotype table with a
different MLST scheme (Pseudomonas-style loci) and assert the exact same core builds a
lineage and detects a reversal — proving nothing is hard-coded to B. multivorans. This is
the honest 'it generalizes' claim: the CODE is shown to be indication-agnostic, without
fabricating a second organism's grounded literature.
"""

from __future__ import annotations

from app.ingestion.upload import build_upload_graph

# A different organism, a different 7-locus scheme (P. aeruginosa MLST locus names).
_PSEUDOMONAS_CSV = """id,acsA,aroE,guaA,mutL,nuoD,ppsA,trpE,year
PA-01,1,1,1,1,1,1,1,2004
PA-02,2,1,1,1,1,1,1,2006
PA-03,2,2,1,1,1,1,1,2008
PA-04,2,2,2,1,1,1,1,2010
PA-05,1,1,1,1,2,1,1,2007
PA-06,1,1,1,1,2,2,1,2009
"""


def test_core_runs_on_a_different_organism_and_scheme():
    graph = build_upload_graph(_PSEUDOMONAS_CSV, organism="Pseudomonas aeruginosa (illustrative)")
    s = graph["summary"]
    assert s["organism"] == "Pseudomonas aeruginosa (illustrative)"
    assert s["loci"] == 7  # the Pseudomonas scheme, not Burkholderia's
    assert s["strains"] == 6
    assert s["roots"] >= 1
    # Graph is well-formed: every edge connects two real nodes; a spanning tree.
    ids = {n["id"] for n in graph["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])
    assert len(graph["edges"]) == len(graph["nodes"]) - s["roots"]


def test_reversal_is_detected_on_any_scheme():
    # Each consecutive pair differs by exactly one locus, forcing an A–B–C–D–E MST
    # chain; acsA runs 1→2→2→2→1, so it is present→absent→present along the path — a
    # reversal the detector must flag with zero Burkholderia knowledge.
    csv = (
        "id,acsA,aroE,guaA,mutL,nuoD,ppsA,trpE\n"
        "A,1,1,1,1,1,1,1\n"
        "B,2,1,1,1,1,1,1\n"
        "C,2,2,1,1,1,1,1\n"
        "D,2,2,2,1,1,1,1\n"
        "E,1,2,2,1,1,1,1\n"
    )
    graph = build_upload_graph(csv, organism="test organism")
    assert graph["summary"]["max_flipper"] >= 1
    assert graph["summary"]["flipper_carrying"] >= 1
