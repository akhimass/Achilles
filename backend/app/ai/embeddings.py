"""Embeddings for the optional pgvector semantic-search path.

Search always works via the deterministic lexical ranker (search_shaping.py). This
module adds a *semantic* layer on top when an embedding provider is configured
(`EMBED_PROVIDER=openai` + key): it embeds paper abstracts into `papers.embedding`
(VECTOR) once, and embeds a query at request time so the router can rank papers by
pgvector cosine distance. Provider "none" (default) → no embeddings, lexical only.

Network lives here (ai/), never in the deterministic core. If the provider is
unavailable, callers fall back to lexical search — never to fabricated vectors.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def provider_enabled() -> bool:
    return settings.embed_provider == "openai" and bool(settings.embed_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a batch of texts via the configured OpenAI-compatible endpoint.

    Returns a list of vectors, or None if the provider is disabled/unreachable. Never
    fabricates vectors.
    """
    if not provider_enabled() or not texts:
        return None
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.embed_base}/embeddings",
                headers={"Authorization": f"Bearer {settings.embed_api_key}"},
                json={"model": settings.embed_model, "input": texts},
            )
        if r.status_code != 200:
            logger.info("embeddings -> %s %s", r.status_code, r.text[:160])
            return None
        data = r.json().get("data") or []
        return [d.get("embedding") for d in data if d.get("embedding")]
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("embeddings error: %s", exc)
        return None


async def embed_query(text: str) -> list[float] | None:
    vecs = await embed_texts([text])
    return vecs[0] if vecs else None
