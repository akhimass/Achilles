"""Optional LLM synthesis for grounded Q&A — phrases retrieved claims, never invents.

The deterministic core (app/qa.py) already retrieved and cited the grounded claims. This
layer asks Claude to compose a 2-3 sentence answer using ONLY those claims, each sentence
citing a claim id — or to refuse. It is strictly opt-in: with no ANTHROPIC_API_KEY (or on
any error) it returns None and the caller falls back to the deterministic summary, so the
ask surface always works and never emits an ungrounded 'AI-slop' answer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai import prompts
from app.ai.client import structured
from app.config import settings
from app.qa import citation_label


class AskSynthesis(BaseModel):
    summary: str
    citations: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    refused: bool = False


def _facts_block(claims: list[dict]) -> str:
    lines: list[str] = []
    for i, c in enumerate(claims, start=1):
        cite = citation_label(c.get("provenance") or {}) or "uncited"
        rel = c.get("relation")
        conf = c.get("confidence")
        meta = ", ".join(
            part for part in [
                f"relation={rel}" if rel else "",
                f"confidence={conf}" if conf is not None else "",
                f"cite={cite}",
            ] if part
        )
        lines.append(f"[{i}] {c.get('title')} ({meta})")
    return "\n".join(lines)


async def synthesize(question: str, persona: str, claims: list[dict]) -> AskSynthesis | None:
    """Compose a grounded answer from the claims, or None if unavailable/failed."""
    if not settings.anthropic_api_key or not claims:
        return None
    try:
        return await structured(
            schema=AskSynthesis,
            system=prompts.ASK_SYSTEM.format(persona=persona),
            user=prompts.ASK_USER.format(question=question, facts=_facts_block(claims)),
            model=settings.model_reason,
        )
    except Exception:
        return None
