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

# A second, DIFFERENT organism + MLST scheme (Pseudomonas aeruginosa locus names), used
# to show the deterministic core is organism-agnostic. Clearly labelled illustrative: the
# profiles are a designed teaching cohort (with two allele reversals), not real isolates —
# so nothing here is misrepresented as grounded biology.
_ILLUSTRATIVE_ALT_CSV = """id,acsA,aroE,guaA,mutL,nuoD,ppsA,trpE,year
ALT-01,1,1,1,1,1,1,1,2004
ALT-02,2,1,1,1,1,1,1,2006
ALT-03,2,2,1,1,1,1,1,2008
ALT-04,2,2,2,1,1,1,1,2010
ALT-05,1,2,2,1,1,1,1,2012
ALT-06,1,1,1,1,2,1,1,2005
ALT-07,1,1,1,1,2,2,1,2007
ALT-08,1,1,1,1,2,2,2,2009
ALT-09,1,1,1,1,1,2,2,2011
ALT-10,1,1,1,2,1,1,1,2006
ALT-11,1,1,1,2,1,1,2,2008
ALT-12,1,1,1,2,2,1,2,2010
ALT-13,2,1,1,2,1,1,1,2013
ALT-14,2,1,1,1,1,1,2,2015
"""


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
async def example(cohort: str = "burkholderia") -> str:
    """Example genotype CSV for the 'try example' affordance.

    `cohort=burkholderia` (default) → REAL public Burkholderia multivorans MLST profiles
    (PubMLST). `cohort=alt` → a DIFFERENT organism/scheme (illustrative teaching cohort)
    that proves the same deterministic core builds a lineage regardless of organism.
    """
    if cohort in ("alt", "illustrative", "pseudomonas"):
        return _ILLUSTRATIVE_ALT_CSV
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
