"""Tamarind Bio — AlphaFold structure prediction for flipper-gene targets (AI/ML).

Achilles' first AI/ML workflow: a flipper gene → its protein (NCBI WP accession) → a
predicted 3D structure with per-residue confidence (pLDDT). Tamarind runs AlphaFold;
RCSB is a fast fallback for proteins with an experimental structure.

Implemented against the documented Tamarind API (https://app.tamarind.bio/api/, auth
header ``x-api-key``):

    POST /validate-job {type, settings, jobName?}  → {valid, normalized, error, ...}
    POST /submit-job   {jobName, type, settings, projectTag?} → "<job> submitted to queue."
    GET  /jobs?jobName=<job> → {jobs:[{JobName, JobStatus, resultUrl, Completed, ...}],
                                 statuses:{...}}
    POST /result {jobName, fileName?} → a presigned URL (quoted string) → GET → zip

Job status is read from ``JobStatus`` ("Complete" | "In Queue" | "Running" | "Stopped"
| "Failed"); finished results download from the job record's ``resultUrl`` (a presigned
S3 zip), falling back to POST /result. Resolved structures are cached under
``data/demo/structures/`` keyed by accession, so the demo serves them offline and never
depends on job timing. All parsing (pLDDT, residue count, status) is deterministic
plain Python.
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

# AlphaFold job type name (from Tamarind GET /tools; used by submit + validate).
ALPHAFOLD_TYPE = "alphafold"

# Documented /submit-job settings with sensible demo defaults. numModels is a STRING
# per the schema; "1" is fast. Callers may override any key.
ALPHAFOLD_DEFAULTS: dict[str, Any] = {
    "numModels": "1",
    "numRecycles": 3,
    "numRelax": 0,
    "useMSA": True,
    "modelType": "auto",
    "msaDatabase": "uniref",
    "templateMode": "pdb100",
}

# JobStatus (from GET /jobs) → normalized state used by callers.
_STATUS_MAP = {
    "complete": "complete",
    "completed": "complete",
    "success": "complete",
    "done": "complete",
    "running": "running",
    "in queue": "running",
    "queued": "running",
    "pending": "running",
    "submitted": "running",
    "failed": "failed",
    "error": "failed",
    "stopped": "failed",
    "cancelled": "failed",
    "canceled": "failed",
}

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


# ─── Deterministic parsing (no network) ──────────────────────────────────────


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


def normalize_status(raw: str | None) -> str:
    """Map a Tamarind JobStatus to complete | running | failed | unknown."""
    return _STATUS_MAP.get((raw or "").strip().lower(), "unknown")


def alphafold_settings(sequence: str, **overrides: Any) -> dict[str, Any]:
    """Build a documented /submit-job settings object for an AlphaFold monomer job."""
    body = {"sequence": sequence, **ALPHAFOLD_DEFAULTS}
    body["numModels"] = str(settings.tamarind_num_models or "1")
    body.update(overrides)
    return body


def _pick_pdb(names: list[str]) -> str | None:
    """Choose the best-ranked (relaxed, rank_001) PDB from a ColabFold results listing."""
    pdbs = [n for n in names if n.lower().endswith(".pdb")]
    if not pdbs:
        return None
    for pref in ("relaxed_rank_001", "rank_001", "rank001", "relaxed"):
        for n in pdbs:
            if pref in n.lower():
                return n
    return sorted(pdbs)[0]


def _extract_pdb(content: bytes, text: str) -> str | None:
    """A results download is either a PDB or a zip of the job outputs."""
    if content[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            pick = _pick_pdb(z.namelist())
            if pick:
                return z.read(pick).decode("utf-8", "ignore")
        except (zipfile.BadZipFile, KeyError):
            return None
        return None
    return text if "ATOM" in text.upper() else None


def _job_record(payload: Any, job_name: str) -> dict | None:
    """Find the record for `job_name` in a GET /jobs response ({jobs:[...]}) or list."""
    jobs = payload.get("jobs") if isinstance(payload, dict) else payload
    if isinstance(jobs, list):
        for j in jobs:
            if isinstance(j, dict) and job_name in (
                j.get("JobName"), j.get("jobName"), j.get("name")
            ):
                return j
        # A jobName filter returns exactly one; if unlabeled, take the sole record.
        if len(jobs) == 1 and isinstance(jobs[0], dict):
            return jobs[0]
    return None


# ─── Network: NCBI sequence, validate, submit, poll, download ─────────────────


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


async def validate_job(job_type: str, job_settings: dict, job_name: str | None = None) -> dict:
    """POST /validate-job — free pre-flight. Returns the parsed body or {} on failure.

    On success the body carries ``valid`` and, when valid, ``normalized`` (settings with
    defaults filled in, ready to submit). Best-effort: never raises.
    """
    if not settings.tamarind_api_key:
        return {}
    payload: dict[str, Any] = {"type": job_type, "settings": job_settings}
    if job_name:
        payload["jobName"] = job_name
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.tamarind_base}validate-job", headers=_headers(), json=payload
            )
        if r.status_code == 200:
            return r.json()
        logger.info("tamarind validate-job -> %s %s", r.status_code, r.text[:160])
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("tamarind validate-job error: %s", exc)
    return {}


async def submit_job(
    job_type: str, job_settings: dict, job_name: str, *, project_tag: str | None = None
) -> tuple[bool, str]:
    """POST /submit-job. Returns (ok, message). 200 = submitted to queue."""
    if not settings.tamarind_api_key:
        return (False, "no api key")
    body: dict[str, Any] = {"jobName": job_name, "type": job_type, "settings": job_settings}
    tag = project_tag or settings.tamarind_project_tag
    if tag:
        body["projectTag"] = tag
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.tamarind_base}submit-job", headers=_headers(), json=body
            )
        ok = r.status_code == 200
        logger.info("tamarind submit %s -> %s %s", job_name, r.status_code, r.text[:160])
        return (ok, r.text[:200])
    except httpx.HTTPError as exc:
        logger.info("tamarind submit error: %s", exc)
        return (False, str(exc))


async def submit_alphafold(sequence: str, job_name: str, *, validate: bool = True) -> bool:
    """Validate (pre-flight) then submit an AlphaFold monomer job for `sequence`."""
    if not settings.tamarind_api_key:
        return False
    job_settings = alphafold_settings(sequence)
    if validate:
        verdict = await validate_job(ALPHAFOLD_TYPE, job_settings, job_name)
        # Block only on an explicit invalid verdict; if validate is unavailable, proceed.
        if verdict and verdict.get("valid") is False:
            logger.info("tamarind validate rejected %s: %s", job_name, verdict.get("error"))
            return False
        if verdict.get("normalized"):
            job_settings = verdict["normalized"]
    ok, _ = await submit_job(ALPHAFOLD_TYPE, job_settings, job_name)
    return ok


async def get_job(job_name: str) -> dict | None:
    """GET /jobs?jobName=<job> → the single job record, or None."""
    if not settings.tamarind_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.get(
                f"{settings.tamarind_base}jobs", headers=_headers(), params={"jobName": job_name}
            )
        if r.status_code == 200:
            return _job_record(r.json(), job_name)
        logger.info("tamarind jobs -> %s %s", r.status_code, r.text[:160])
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("tamarind jobs error: %s", exc)
    return None


async def poll_job(job_name: str, *, max_wait: int = 0, interval: int = 6) -> tuple[str, str | None]:
    """Poll GET /jobs for `job_name`. Returns (state, result_url).

    state ∈ {complete, running, failed, unknown, no_key}. `result_url` is the presigned
    zip from the job record when complete. Short/zero max_wait keeps the request
    non-blocking; callers treat 'running' as pending.
    """
    if not settings.tamarind_api_key:
        return ("no_key", None)
    waited = 0
    while True:
        rec = await get_job(job_name)
        state = (
            normalize_status(rec.get("JobStatus") or rec.get("status") or rec.get("state"))
            if rec
            else "unknown"
        )
        if state == "complete":
            return ("complete", rec.get("resultUrl") or rec.get("ResultUrl"))
        if state == "failed":
            return ("failed", None)
        if waited >= max_wait:
            return (state, None)
        await asyncio.sleep(interval)
        waited += interval


async def _download_url(client: httpx.AsyncClient, url: str) -> str | None:
    dl = await client.get(url)
    if dl.status_code == 200:
        return _extract_pdb(dl.content, dl.text)
    return None


async def download_result(job_name: str, *, result_url: str | None = None) -> str | None:
    """Download a finished job's PDB.

    Prefers the job record's presigned ``resultUrl``; otherwise calls POST /result
    (which returns a quoted presigned URL) and downloads that. Returns PDB text.
    """
    if not settings.tamarind_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
            if result_url:
                pdb = await _download_url(client, result_url)
                if pdb:
                    return pdb
            # Fallback: ask /result for a fresh presigned URL to the results zip.
            r = await client.post(
                f"{settings.tamarind_base}result", headers=_headers(), json={"jobName": job_name}
            )
            if r.status_code != 200:
                return None
            body = r.text.strip().strip('"')
            if body.startswith("http"):
                return await _download_url(client, body)
            return _extract_pdb(r.content, r.text)
    except httpx.HTTPError as exc:
        logger.info("tamarind result error: %s", exc)
        return None


# ─── RCSB fallback (experimental structures) ─────────────────────────────────


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


# ─── Orchestration ───────────────────────────────────────────────────────────


def _complete_payload(locus_tag, wp, name, product, pdb, job) -> dict:
    return {
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


async def get_structure(
    locus_tag: str, wp: str | None, name: str | None, product: str | None, *, submit: bool = True
) -> dict:
    """Resolve a 3D structure for a gene: cache → finished AlphaFold job → RCSB →
    (optionally) submit a fresh AlphaFold job. Returns a JSON-able payload."""
    cache_key = wp or locus_tag
    cache_file = _cache_dir() / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', cache_key)}.json"
    if cache_file.exists():
        try:
            payload = json.loads(cache_file.read_text())
            payload["from_cache"] = True
            return payload
        except (ValueError, OSError):
            pass

    job = _job_name(locus_tag)

    # An AlphaFold job may already exist for this gene — check (non-blocking).
    job_state: str | None = None
    if settings.tamarind_api_key:
        job_state, result_url = await poll_job(job, max_wait=0)
        if job_state == "complete":
            pdb = await download_result(job, result_url=result_url)
            if pdb:
                payload = _complete_payload(locus_tag, wp, name, product, pdb, job)
                cache_file.write_text(json.dumps(payload))
                return payload

    rcsb = await get_rcsb_structure(name or "", product or "")
    if rcsb:
        payload = {"locus_tag": locus_tag, "wp": wp, "name": name, "product": product,
                   "status": "complete", **rcsb}
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
        if seq and await submit_alphafold(seq, job):
            return {
                "locus_tag": locus_tag, "wp": wp, "name": name, "product": product,
                "source": "alphafold_pending", "pdb": None, "status": "running", "job_name": job,
                "note": "AlphaFold job submitted — poll again shortly.",
            }

    return {
        "locus_tag": locus_tag, "wp": wp, "name": name, "product": product,
        "source": "unavailable", "pdb": None, "status": "unavailable",
        "note": "No cached, predicted, or experimental structure available yet.",
    }
