"""Reader for pre-reviewed, committed LLM narration (network-free).

The demo serves *fixed, pre-reviewed, cited* narration from a committed cache instead
of calling the model per visitor — faster, cheaper, reproducible, and auditable. This
module only READS the committed cache under ``data/demo/narration/``; the cache is
produced once by ``app/sources/make_narration_snapshot.py`` (which needs an API key).

If the cache is absent or empty (e.g. no key was available when seeding), callers fall
back to the deterministic rationale — we never fabricate narration. Cached entries
carry the same citations the live path would, plus the model id and a timestamp, so a
judge can audit exactly what produced them.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

NARRATION_DIR = Path(__file__).resolve().parents[2] / "data" / "demo" / "narration"
TARGETS_FILE = NARRATION_DIR / "targets.json"
CYCLE_FILE = NARRATION_DIR / "cycle.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


@lru_cache(maxsize=1)
def _target_cache() -> dict:
    return _load(TARGETS_FILE)


@lru_cache(maxsize=1)
def _cycle_cache() -> dict:
    return _load(CYCLE_FILE)


def load_target_rationales() -> dict:
    """All cached target rationales keyed by locus_tag (``{}`` if none)."""
    return dict(_target_cache())


def load_cycle_narratives() -> dict:
    """All cached cycle narratives keyed by organism (``{}`` if none)."""
    return dict(_cycle_cache())


def target_rationale(locus_tag: str | None) -> dict | None:
    """Cached rationale for one target locus, or None. Shape:
    ``{narrative, citations, model, generated_at}``."""
    if not locus_tag:
        return None
    entry = _target_cache().get(locus_tag)
    return entry if isinstance(entry, dict) and entry.get("narrative") else None


def cycle_narrative(organism: str | None) -> dict | None:
    """Cached cycle narrative for one organism, or None. Shape:
    ``{summary, caveats, citations, model, generated_at}``."""
    if not organism:
        return None
    entry = _cycle_cache().get(organism)
    return entry if isinstance(entry, dict) and entry.get("summary") else None


def reset_cache() -> None:
    """Clear the memoized reads (used by the snapshot builder and by tests)."""
    _target_cache.cache_clear()
    _cycle_cache.cache_clear()
