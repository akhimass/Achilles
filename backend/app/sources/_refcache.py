"""Tiny committed file-cache for public reference lookups (CARD/ARO, UniProt).

Cached under data/demo/reference/ so grounding is reproducible offline after the
first fetch. Everything here is public reference data, safe to commit.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

REF_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "reference"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "q"


def _path(kind: str, key: str) -> Path:
    h = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()[:8]
    return REF_DIR / f"{kind}-{_slug(key)}-{h}.json"


def load(kind: str, key: str) -> Any | None:
    p = _path(kind, key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def save(kind: str, key: str, value: Any) -> None:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    _path(kind, key).write_text(json.dumps(value, indent=2))
