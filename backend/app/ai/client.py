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


async def structured(
    *,
    schema: type[T],
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 4096,
) -> T:
    """Call Claude and parse the reply into `schema`.

    The system prompt must instruct the model to return ONLY JSON matching the
    schema (see prompts.py). We defensively strip code fences before parsing.
    """
    resp = await _client.messages.create(
        model=model or settings.model_extract,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text[4:] if text.startswith("json") else text
        text = text.rsplit("```", 1)[0].strip()
    return schema.model_validate(json.loads(text))
