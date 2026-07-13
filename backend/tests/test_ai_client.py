"""AI client resilience — no live API, no DB.

Locks two things we rely on so a batch corpus build (and the live Ask path) degrade
gracefully instead of crashing:
  1. JSON salvage tolerates code fences and a prose preamble around the object.
  2. A model refusal (AMR text intermittently trips the safety classifier) skips the paper
     rather than raising — no claims from a refused abstract, consistent with the graph's
     "provenance or it doesn't exist" rule.
"""

from __future__ import annotations

import asyncio

from app.ai import extraction
from app.ai.client import ModelRefusal, _json_from_text
from app.models.domain import Paper


def test_json_salvage_tolerates_fences_and_preamble():
    assert _json_from_text('```json\n{"claims": []}\n```') == '{"claims": []}'
    assert _json_from_text('```\n{"claims": []}\n```') == '{"claims": []}'
    assert _json_from_text('Sure, here is the result:\n{"claims": []}\nHope that helps!') == '{"claims": []}'
    assert _json_from_text('{"claims": []}') == '{"claims": []}'


def test_extract_claims_skips_refused_paper(monkeypatch):
    async def _refuse(**_kwargs):
        raise ModelRefusal("safety refusal")

    monkeypatch.setattr(extraction, "structured", _refuse)
    paper = Paper(pmid="1", title="t", abstract="MarR inactivation confers resistance to ciprofloxacin.")
    result = asyncio.run(extraction.extract_claims(paper))
    assert result.claims == []  # refused → no claims, but no exception


def test_extract_claims_no_abstract_is_empty():
    result = asyncio.run(extraction.extract_claims(Paper(pmid="1", title="t", abstract="")))
    assert result.claims == []
