"""Bridge — the researcher→physician translation. Pure checks, no DB.

Both lenses must be built ONLY from grounded edges + a cited cycle; provenance is carried
across the handoff; and when there's nothing to translate it says so rather than guess.
"""

from __future__ import annotations

import asyncio

from app.bridge_shaping import shape_bridge
from app.routers.bridge import bridge

_GENE = {"locus": "A8H40_RS07590", "name": "MarR", "product": "MarR family regulator"}

_EDGES = [
    {"relation": "implicates", "target": "AcrAB-TolC efflux pump",
     "provenance": {"pmid": "42106608", "pubmed_url": "u1", "db": "CARD", "acc": "ARO:3003378",
                    "ref_url": "r1"}},
    {"relation": "confers_resistance", "target": "ciprofloxacin",
     "provenance": {"pmid": "40855113", "pubmed_url": "u2", "db": "CARD", "acc": "ARO:3003378",
                    "ref_url": "r2"}},
]

_CYCLE = {
    "cycle": ["meropenem", "trimethoprim-sulfamethoxazole", "ceftazidime"],
    "summary": "3-drug cycle",
    "rcs_pairs": [
        {"drug_a": "meropenem", "drug_b": "trimethoprim-sulfamethoxazole",
         "provenance": {"pmid": "32335276", "pubmed_url": "u3"}},
    ],
}


def test_bridge_builds_both_lenses_from_grounded_data():
    b = shape_bridge(_GENE, _EDGES, target={"rank_score": 0.57, "structure_available": True},
                     cycle=_CYCLE, organism="Burkholderia multivorans")
    # researcher lens: mechanism + cited claims + the ranked target
    assert b["research"]["lens"] == "Target identification"
    assert "AcrAB-TolC efflux pump" in b["research"]["mechanism"]
    assert b["research"]["target"]["rank_score"] == 0.57
    assert all(c["citation"] for c in b["research"]["grounded_claims"])
    # physician lens: drives-resistance + cited collateral opening + caveats
    assert "ciprofloxacin" in b["clinic"]["drives_resistance_to"]
    assert b["clinic"]["collateral_opening"]["citation"]["label"] == "PMID 32335276"
    assert any("NOT a treatment recommendation" in c for c in b["clinic"]["caveats"])
    # the handoff carries provenance across
    assert b["provenance_carried"] >= 3
    assert "provenance carried" in b["handoff"]


def test_bridge_is_honest_when_nothing_to_translate():
    b = shape_bridge({"locus": "L9", "name": "orphan", "product": "hypothetical"},
                     grounded_edges=[], target=None, cycle=None, organism="Testium")
    assert b["clinic"]["drives_resistance_to"] == []
    assert b["clinic"]["collateral_opening"] is None
    assert "rather than guess" in b["clinic"]["actionable"]
    assert b["provenance_carried"] == 0


def test_only_grounded_edges_with_citations_become_claims():
    edges = _EDGES + [{"relation": "implicates", "target": "uncited thing", "provenance": {}}]
    b = shape_bridge(_GENE, edges, organism="X")
    assert all(c["citation"] for c in b["research"]["grounded_claims"])
    assert not any(c["target"] == "uncited thing" for c in b["research"]["grounded_claims"])


# --- Router-level regression: the handler must read the DB row by its real column
# name (`locus_tag`, per _GENE_SQL), not `locus`. A wrong key 500s every real gene
# (NoSuchColumnError) — which the pure shape tests above cannot catch. ---

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeSession:
    """Returns canned mappings keyed off the SQL text, mimicking a live gene row."""

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        if "FROM genes WHERE locus_tag" in sql:
            # Note: the real query aliases the column as `locus_tag`, not `locus`.
            return _FakeResult([{"locus_tag": "A8H40_RS07590", "name": "MarR",
                                 "product": "MarR family regulator", "wp": "WP_1"}])
        if "FROM evidence_edges" in sql:
            return _FakeResult([{"relation": "confers_resistance", "target": "ciprofloxacin",
                                 "provenance_pmid": "40855113", "provenance_db": "CARD",
                                 "provenance_acc": "ARO:3003378"}])
        if "FROM targets" in sql:
            return _FakeResult([{"rank_score": 0.57, "tractability": {"bucket": "novel"},
                                 "pdb_ids": []}])
        return _FakeResult([])  # collateral pairs — empty is fine (cycle=None)


def test_bridge_router_reads_gene_row_by_real_column_name():
    out = asyncio.run(bridge(gene="A8H40_RS07590", organism="Burkholderia multivorans",
                             session=_FakeSession()))
    assert out["found"] is True
    assert out["gene"]["locus"] == "A8H40_RS07590"
    assert "ciprofloxacin" in out["clinic"]["drives_resistance_to"]
    assert out["provenance_carried"] >= 1
