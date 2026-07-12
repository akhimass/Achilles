"""Tamarind Bio — AlphaFold structure prediction for flipper-gene targets (AI/ML).

This is Achilles' first AI/ML workflow: a flipper gene → its protein (NCBI WP
accession) → a predicted 3D structure with per-residue confidence (pLDDT). Tamarind
runs AlphaFold; RCSB is a fast fallback for proteins with an experimental structure.

API (https://app.tamarind.bio/api/, auth header ``x-api-key``):
    POST submit-job {type: alphafold, settings:{sequence,...}}
    GET  jobs                → status + output files
    POST result {jobName, path} → PDB text

Fresh implementation for this repo. Results are cached to ``data/tamarind/`` keyed by
protein accession, so a resolved structure is served instantly and the demo does not
depend on job timing. Deterministic parsing (pLDDT, residue count) is plain Python.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Known experimental structures for common products (fast, free RCSB fallback).
RCSB_HINTS: dict[str, str] = {
    "marr": "1JGS",  # MarR multidrug-resistance regulator
    "dna gyrase subunit b": "1KZN",
    "recombinase a": "2REB",
    "50s ribosomal protein l1": "1CJS",
    "elongation factor": "1WDT",
    "tryptophan synthase": "1WSY",
}


def _cache_dir() -> Path:
    # Under data/demo/ so resolved structures (incl. the committed MarR AlphaFold
    # showcase) ship with the repo and the demo serves them offline.
    d = Path(__file__).resolve().parents[3] / "data" / "demo" / "structures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _headers() -> dict[str, str]:
    key = settings.tamarind_api_key
    return {"x-api-key": key} if key else {}


def _job_name(locus_tag: str) -> str:
    return "achilles_af_" + re.sub(r"[^a-z0-9]+", "", locus_tag.lower())


def plddt_from_pdb(pdb_text: str, sample: int = 4000) -> float | None:
    """Mean B-factor over ATOM lines — pLDDT for AlphaFold PDBs (0–100)."""
    vals: list[float] = []
    for line in pdb_text.splitlines():
        if line.startswith("ATOM") and len(line) >= 66:
            try:
                vals.append(float(line[60:66]))
            except ValueError:
                continue
            if len(vals) >= sample:
                break
    if not vals:
        return None
    return round(min(100.0, max(0.0, sum(vals) / len(vals))), 1)


def residue_count_from_pdb(pdb_text: str) -> int:
    residues: set[tuple[str, str]] = set()
    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) > 26:
            residues.add((line[21:22], line[22:26].strip()))
    return len(residues)


async def fetch_protein_sequence(wp: str) -> str | None:
    """Fetch a protein AA sequence from NCBI by accession (e.g. WP_006410546.1)."""
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.get(
            f"{settings.ncbi_eutils_base}/efetch.fcgi",
            params={"db": "protein", "id": wp, "rettype": "fasta", "retmode": "text"},
        )
    if r.status_code != 200 or ">" not in r.text:
        return None
    return "".join(l.strip() for l in r.text.splitlines() if l and not l.startswith(">"))


async def submit_alphafold(sequence: str, job_name: str) -> bool:
    if not settings.tamarind_api_key:
        return False
    body = {
        "jobName": job_name,
        "type": "alphafold",
        "settings": {"sequence": sequence, "numModels": "1", "numRecycles": 1, "numRelax": 0, "useMSA": True},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{settings.tamarind_base}submit-job", headers=_headers(), json=body)
    ok = r.status_code == 200
    logger.info("tamarind submit %s -> %s %s", job_name, r.status_code, r.text[:120])
    return ok


def _find_job(payload: Any, job_name: str) -> dict | None:
    if isinstance(payload, dict):
        if job_name in (payload.get("JobName"), payload.get("jobName"), payload.get("name")):
            return payload
        for k in ("jobs", "data", "items", "results"):
            hit = _find_job(payload.get(k), job_name)
            if hit:
                return hit
    elif isinstance(payload, list):
        for j in payload:
            hit = _find_job(j, job_name)
            if hit:
                return hit
    return None


def _pdb_path_from_record(rec: dict) -> str | None:
    """The finished PDB path lives in the Score JSON ('Pdb Path')."""
    score = rec.get("Score")
    if isinstance(score, str):
        try:
            score = json.loads(score)
        except Exception:
            score = {}
    if isinstance(score, dict) and score.get("Pdb Path"):
        return str(score["Pdb Path"])
    raw = rec.get("outputs") or rec.get("outputFiles") or rec.get("files") or []
    for o in raw if isinstance(raw, list) else []:
        p = o if isinstance(o, str) else (o.get("path") or o.get("file"))
        if p and str(p).lower().endswith(".pdb"):
            return str(p)
    return None


async def poll_job(job_name: str, *, max_wait: int = 20, interval: int = 6) -> tuple[str, str | None]:
    """Poll GET /jobs. Returns (state, pdb_output_path). Short max_wait keeps the
    request non-blocking; callers treat 'running' as pending."""
    if not settings.tamarind_api_key:
        return ("no_key", None)
    waited = 0
    async with httpx.AsyncClient(timeout=40) as client:
        while waited <= max_wait:
            r = await client.get(f"{settings.tamarind_base}jobs", headers=_headers())
            rec = _find_job(r.json(), job_name) if r.status_code == 200 else None
            if rec:
                status = str(
                    rec.get("JobStatus") or rec.get("status") or rec.get("state") or ""
                ).lower()
                if status in ("complete", "completed", "success", "done"):
                    return ("complete", _pdb_path_from_record(rec))
                if status in ("failed", "error", "cancelled", "canceled"):
                    return ("failed", None)
            if waited >= max_wait:
                break
            await asyncio.sleep(interval)
            waited += interval
    return ("running", None)


def _extract_pdb(content: bytes, text: str) -> str | None:
    """A /result download is either a PDB or a zip of the job outputs."""
    if content[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            pdbs = [n for n in z.namelist() if n.lower().endswith(".pdb")]
            if pdbs:
                pick = next((n for n in pdbs if "rank_001" in n), pdbs[0])
                return z.read(pick).decode("utf-8", "ignore")
        except Exception:
            return None
    return text if "ATOM" in text.upper() else None


async def download_result(job_name: str, path: str) -> str | None:
    """POST /result → signed URL → download (PDB or zip) → PDB text."""
    if not settings.tamarind_api_key:
        return None
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        r = await client.post(
            f"{settings.tamarind_base}result", headers=_headers(), json={"jobName": job_name, "path": path}
        )
        if r.status_code != 200:
            return None
        body = r.text.strip()
        if body.startswith('"http') or body.startswith("http"):
            url = body.strip('"')
            dl = await client.get(url)
            if dl.status_code == 200:
                return _extract_pdb(dl.content, dl.text)
        return _extract_pdb(r.content, r.text)
    return None


async def get_rcsb_structure(name: str, product: str) -> dict | None:
    key = (name or "").lower().strip()
    pdb_id = RCSB_HINTS.get(key)
    for hint, pid in RCSB_HINTS.items():
        if not pdb_id and hint in (product or "").lower():
            pdb_id = pid
    if not pdb_id:
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"https://files.rcsb.org/download/{pdb_id}.pdb")
    if r.status_code != 200:
        return None
    return {
        "source": "rcsb",
        "pdb": r.text,
        "pdb_id": pdb_id,
        "plddt": None,
        "residue_count": residue_count_from_pdb(r.text),
    }


async def get_structure(
    locus_tag: str, wp: str | None, name: str | None, product: str | None, *, submit: bool = True
) -> dict:
    """Resolve a 3D structure for a gene: cache → running AlphaFold job → RCSB →
    (optionally) submit a fresh AlphaFold job. Returns a JSON-able payload."""
    cache_key = wp or locus_tag
    cache_file = _cache_dir() / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', cache_key)}.json"
    if cache_file.exists():
        try:
            payload = json.loads(cache_file.read_text())
            payload["from_cache"] = True
            return payload
        except Exception:
            pass

    job = _job_name(locus_tag)

    # An AlphaFold job may already exist for this gene — check briefly.
    job_state: str | None = None
    if settings.tamarind_api_key:
        job_state, out = await poll_job(job, max_wait=0)
        if job_state == "complete" and out:
            pdb = await download_result(job, out)
            if pdb:
                payload = {
                    "locus_tag": locus_tag,
                    "wp": wp,
                    "name": name,
                    "product": product,
                    "source": "alphafold",
                    "pdb": pdb,
                    "plddt": plddt_from_pdb(pdb),
                    "residue_count": residue_count_from_pdb(pdb),
                    "job_name": job,
                    "status": "complete",
                }
                cache_file.write_text(json.dumps(payload))
                return payload

    rcsb = await get_rcsb_structure(name or "", product or "")
    if rcsb:
        payload = {"locus_tag": locus_tag, "wp": wp, "name": name, "product": product, "status": "complete", **rcsb}
        cache_file.write_text(json.dumps(payload))
        return payload

    # A job is already folding this protein — report pending rather than "fold me".
    if job_state == "running":
        return {
            "locus_tag": locus_tag, "wp": wp, "name": name, "product": product,
            "source": "alphafold_pending", "pdb": None, "status": "running", "job_name": job,
            "note": "AlphaFold job running on Tamarind — reselect shortly.",
        }

    if submit and settings.tamarind_api_key and wp:
        seq = await fetch_protein_sequence(wp)
        if seq:
            await submit_alphafold(seq, job)
            return {
                "locus_tag": locus_tag,
                "wp": wp,
                "name": name,
                "product": product,
                "source": "alphafold_pending",
                "pdb": None,
                "status": "running",
                "job_name": job,
                "note": "AlphaFold job submitted — poll again shortly.",
            }

    return {
        "locus_tag": locus_tag,
        "wp": wp,
        "name": name,
        "product": product,
        "source": "unavailable",
        "pdb": None,
        "status": "unavailable",
        "note": "No cached, predicted, or experimental structure available yet.",
    }
