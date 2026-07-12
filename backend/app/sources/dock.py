"""Docking + ADMET beat via Tamarind Bio — tractability → structure → cited inhibitor.

For each target with a cited known inhibitor (data/demo/docking/ligands.json), this:
  1. runs Tamarind **ADMET** on the ligand SMILES → drug-property prediction, and
  2. docks the ligand into the target's AlphaFold structure (uploads the cached PDB as
     the receptor, submits the configured docking tool) → pose + score,
then caches the result under data/demo/docking/results/<locus>.json so /api/docking can
serve it. Every ligand traces to a GROUNDED evidence edge, so the beat starts from real
cited chemistry — never an invented molecule. No fabricated pose/score: values are only
written when a real Tamarind job returns them.

Requires TAMARIND_API_KEY (+ the target's structure cached). Run:  python -m app.sources.dock
"""

from __future__ import annotations

import asyncio
import json

from app.ai import docking_cache, tamarind
from app.config import settings
from app.ingestion.seed import PUBLIC_REFERENCE_GENES

_WP_BY_LOCUS = {g["locus_tag"]: g.get("wp") for g in PUBLIC_REFERENCE_GENES}


def _parse_admet(files: dict[str, bytes]) -> dict | None:
    for name, data in files.items():
        low = name.lower()
        if low.endswith(".json"):
            try:
                return {"source_file": name, "properties": json.loads(data.decode("utf-8", "ignore"))}
            except ValueError:
                continue
        if low.endswith(".csv"):
            text = data.decode("utf-8", "ignore").strip().splitlines()
            if len(text) >= 2:
                header = [h.strip() for h in text[0].split(",")]
                row = [c.strip() for c in text[1].split(",")]
                return {"source_file": name, "properties": dict(zip(header, row))}
    return None


def _parse_docking(files: dict[str, bytes]) -> dict | None:
    import re

    poses = [n for n in files if n.lower().endswith((".pdb", ".sdf", ".mol2"))]
    if not poses:
        return None
    score = None
    for name, data in files.items():
        if not name.lower().endswith((".json", ".csv")):
            continue
        txt = data.decode("utf-8", "ignore")
        low = txt.lower()
        for key in ("confidence", "score", "affinity", "vina"):
            idx = low.find(key)
            if idx == -1:
                continue
            m = re.search(r"[-+]?\d+\.?\d*", txt[idx + len(key) : idx + len(key) + 40])
            if m:
                try:
                    score = float(m.group())
                except ValueError:
                    pass
            break
        if score is not None:
            break
    return {"pose_available": True, "pose_file": sorted(poses)[0], "score": score}


async def _admet(smiles: str, job: str) -> dict | None:
    settings_body = {"smilesStrings": [smiles]}
    verdict = await tamarind.validate_job("admet", settings_body, job)
    if verdict.get("normalized"):
        settings_body = verdict["normalized"]
    ok, _ = await tamarind.submit_job("admet", settings_body, job)
    if not ok:
        return None
    state, url = await tamarind.poll_job(job, max_wait=settings.tamarind_poll_max_seconds, interval=15)
    if state != "complete":
        return None
    return _parse_admet(await tamarind.download_result_files(job, result_url=url))


async def _dock(locus: str, smiles: str, job: str) -> dict | None:
    # Receptor = the cached AlphaFold structure; upload it, then dock the ligand in.
    wp = _WP_BY_LOCUS.get(locus)
    cache_file = tamarind._cache_dir() / f"{(wp or locus)}.json".replace("/", "_")
    if not cache_file.exists():
        print(f"  {locus}: no cached structure to dock into — run fold_targets first")
        return None
    pdb = (json.loads(cache_file.read_text()) or {}).get("pdb")
    if not pdb:
        return None
    receptor = f"{job}_receptor.pdb"
    await tamarind.upload_file(receptor, pdb.encode())
    body = {"proteinFile": receptor, "ligand": smiles, "smiles": smiles}
    verdict = await tamarind.validate_job(settings.tamarind_dock_tool, body, job)
    if verdict and verdict.get("valid") is False:
        print(f"  {locus}: dock validate rejected — {verdict.get('error')}. "
              f"Confirm tool name via GET /tools (set TAMARIND_DOCK_TOOL).")
        return None
    if verdict.get("normalized"):
        body = verdict["normalized"]
    ok, _ = await tamarind.submit_job(settings.tamarind_dock_tool, body, job)
    if not ok:
        return None
    state, url = await tamarind.poll_job(job, max_wait=settings.tamarind_poll_max_seconds, interval=15)
    if state != "complete":
        return None
    return _parse_docking(await tamarind.download_result_files(job, result_url=url))


async def dock_all() -> None:
    if not settings.tamarind_api_key:
        print("dock: no TAMARIND_API_KEY — nothing run. Set it to run ADMET + docking via Tamarind.")
        return
    ligands = docking_cache.load_ligands()
    docking_cache.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for locus, ligs in ligands.items():
        for lig in ligs:
            smiles, name = lig.get("smiles"), lig.get("name")
            if not smiles:
                continue
            base = tamarind._job_name(locus)
            print(f"  {locus} / {name}: ADMET…")
            admet = await _admet(smiles, f"{base}_admet")
            print(f"  {locus} / {name}: docking into AlphaFold structure…")
            docking = await _dock(locus, smiles, f"{base}_dock")
            result = {"ligand": name, "smiles": smiles, "citation": lig.get("citation"),
                      "admet": admet, "docking": docking}
            (docking_cache.RESULTS_DIR / f"{locus}.json").write_text(json.dumps(result, indent=2))
            print(f"  {locus} / {name}: cached (admet={'y' if admet else 'n'}, "
                  f"dock={'y' if docking else 'n'})")
    docking_cache.reset_cache()
    print("dock: done — see data/demo/docking/results/")


if __name__ == "__main__":
    asyncio.run(dock_all())
