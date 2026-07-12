"""Bring-your-own-strains ingest: upload a genotype CSV → lineage + flippers.

Stateless and deterministic — the caller's table is parsed and run through the same
core as the seeded demo, and the resulting lineage graph is returned directly (no DB
write, no LLM). Body is raw CSV text (no multipart dependency); a real public example
is served for the "try example" affordance.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.ingestion.upload import UploadError, build_upload_graph

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_PUBMLST = Path(__file__).resolve().parents[3] / "data" / "demo" / "bmultivorans_pubmlst.json"
_MLST_LOCI = ("atpD", "gltB", "gyrB", "lepA", "phaC", "recA", "trpB")


@router.post("/upload")
async def upload(request: Request, organism: str = "uploaded cohort") -> dict:
    """Parse an uploaded genotype CSV (raw text body) into a lineage graph."""
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty upload — send CSV text in the body.")
    if len(body) > 4_000_000:
        raise HTTPException(status_code=400, detail="File too large (max ~4 MB).")
    try:
        return build_upload_graph(body, organism=organism)
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — never leak a stack trace to the client
        raise HTTPException(status_code=400, detail=f"Could not process upload: {exc}") from exc


@router.get("/example", response_class=PlainTextResponse)
async def example() -> str:
    """A real, public example CSV (Burkholderia multivorans MLST profiles, PubMLST) so
    the UI's 'try example' runs the pipeline on genuine data."""
    if not _PUBMLST.exists():
        # Minimal synthetic fallback with an obvious gyrB reversal.
        return (
            "id,atpD,gltB,gyrB,lepA,phaC,recA,trpB,year\n"
            "A,1,1,1,1,1,1,1,2001\nB,1,1,2,1,1,1,1,2003\n"
            "C,1,1,1,1,1,1,1,2005\nD,1,1,2,1,1,1,1,2007\n"
        )
    records = json.loads(_PUBMLST.read_text()).get("records", [])[:28]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", *_MLST_LOCI, "year", "country"])
    for r in records:
        prof = r.get("profile", {})
        w.writerow(
            [r.get("id"), *[prof.get(l, "") for l in _MLST_LOCI], r.get("year", ""), r.get("country", "")]
        )
    return buf.getvalue()
