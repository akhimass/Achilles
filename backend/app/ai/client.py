"""Thin wrapper around the Anthropic SDK.

Two rules enforced here so callers can't get them wrong:
  1. Models are read from config, never passed as literals by feature code.
  2. `structured()` always returns parsed JSON validated against a Pydantic model,
     so no downstream code ever sees raw model text.

The model is a *translator of text into typed claims*, not a computer. Nothing in
this layer should ever be asked to produce a number that a deterministic function
could produce instead.
"""

from __future__ import annotations

import json
from typing import TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.config import settings

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

T = TypeVar("T", bound=BaseModel)


class ModelRefusal(RuntimeError):
    """Claude declined to answer (`stop_reason == "refusal"`).

    Antimicrobial-resistance text — genes that "confer resistance", efflux pumps, drug
    names — is dual-use-adjacent and intermittently trips the model's safety classifier,
    which returns an empty turn. That's not a parse bug and a retry won't fix it, so we
    surface it as its own signal and let each caller decide how to degrade (extraction
    skips the paper; ask falls back to the deterministic summary).
    """


def _json_from_text(text: str) -> str:
    """Salvage a JSON object from model text, tolerating code fences or a prose preamble.

    The extraction/grounding prompts ask for JSON only, but a reasoning model occasionally
    wraps it in fences or a sentence. Rather than force a tool call — which we measured to
    suppress reasoning and hollow out extraction — we let the model reason freely and pull
    the JSON object out here.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text[4:] if text.startswith("json") else text
        text = text.rsplit("```", 1)[0].strip()
    # If prose still surrounds it, take the outermost {...} span.
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return text


async def structured(
    *,
    schema: type[T],
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 4096,
) -> T:
    """Call Claude and parse the reply into `schema`.

    The system prompt instructs the model to return ONLY JSON matching the schema (see
    prompts.py). The model reasons in text and emits the JSON; we salvage it defensively.

    Two deliberate choices, both measured:
      - We do NOT force a tool call. Forcing structured output removes the model's room to
        reason before answering, which hollowed out the reasoning-heavy extraction path
        (empty claim lists). Free-form reasoning + defensive JSON salvage extracts better.
      - We retry once on a parse/validation miss. The model very occasionally returns an
        empty or non-JSON turn; a single retry recovers it deterministically-enough without
        masking a real prompt/schema bug (which would fail both attempts).

    The system prompt is marked cacheable so a batch of calls sharing it can reuse the
    prefix once it clears the provider's cache-minimum size.
    """
    system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    last_err: Exception | None = None
    for _ in range(2):
        resp = await _client.messages.create(
            model=model or settings.model_extract,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason == "refusal":
            raise ModelRefusal("model declined to answer (safety refusal)")
        text = "".join(block.text for block in resp.content if block.type == "text")
        try:
            return schema.model_validate(json.loads(_json_from_text(text)))
        except ValueError as err:  # JSONDecodeError and pydantic ValidationError are ValueErrors
            last_err = err
    raise last_err  # type: ignore[misc]
