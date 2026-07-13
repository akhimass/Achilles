"""Extraction agent: one abstract in, typed claims out.

This is one of only two places an LLM sees raw text. Output is validated against a
Pydantic schema before anything downstream touches it. Claims are NOT yet edges —
they must pass through grounding first (grounding.py).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import ModelRefusal, structured
from app.config import settings
from app.models.domain import Paper


class ExtractedClaim(BaseModel):
    subject: str
    relation: str
    object: str
    object_kind: str
    evidence_span: str
    confidence: float = Field(ge=0, le=1)


class ExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


async def extract_claims(paper: Paper) -> ExtractionResult:
    """Extract structured resistance claims from a paper's abstract.

    A refused abstract (the safety classifier occasionally trips on AMR text) simply
    contributes no claims — we skip it rather than crash the whole corpus build. No claims
    means no edges from this paper, which is consistent with "provenance or it doesn't exist."
    """
    if not paper.abstract:
        return ExtractionResult(claims=[])
    try:
        return await structured(
            schema=ExtractionResult,
            system=prompts.EXTRACT_SYSTEM,
            user=prompts.EXTRACT_USER.format(
                pmid=paper.pmid or "n/a",
                title=paper.title,
                abstract=paper.abstract,
            ),
            model=settings.model_extract,
        )
    except ModelRefusal:
        return ExtractionResult(claims=[])
