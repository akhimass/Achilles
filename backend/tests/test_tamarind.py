"""Tests for the Tamarind adapter's deterministic helpers — no network, no key.

These lock the parsing that aligns with the documented Tamarind API: JobStatus →
normalized state, the documented AlphaFold settings shape, results-zip extraction, and
the /jobs record lookup (which carries resultUrl).
"""

from __future__ import annotations

import io
import zipfile

from app.ai import tamarind


def test_normalize_status_covers_documented_values():
    assert tamarind.normalize_status("Complete") == "complete"
    assert tamarind.normalize_status("In Queue") == "running"
    assert tamarind.normalize_status("Running") == "running"
    assert tamarind.normalize_status("Stopped") == "failed"
    assert tamarind.normalize_status("Failed") == "failed"
    assert tamarind.normalize_status("") == "unknown"
    assert tamarind.normalize_status(None) == "unknown"


def test_alphafold_settings_shape_matches_docs():
    s = tamarind.alphafold_settings("MKT:AYIA")
    assert s["sequence"] == "MKT:AYIA"
    assert isinstance(s["numModels"], str)  # docs: numModels is a string "1".."5"
    assert s["numRelax"] == 0 and s["useMSA"] is True
    assert s["modelType"] == "auto" and s["msaDatabase"] == "uniref"
    # Overrides win.
    assert tamarind.alphafold_settings("X", numModels="5")["numModels"] == "5"


def test_pick_pdb_prefers_relaxed_rank_001():
    names = [
        "achills/config.json",
        "achills/unrelaxed_rank_002_model.pdb",
        "achills/relaxed_rank_001_alphafold2_model.pdb",
        "achills/unrelaxed_rank_001_model.pdb",
    ]
    assert tamarind._pick_pdb(names) == "achills/relaxed_rank_001_alphafold2_model.pdb"
    assert tamarind._pick_pdb(["a/x.json"]) is None  # no pdb


_PDB = (
    "ATOM      1  N   MET A   1      -8.901   4.127  -0.555  1.00 88.50           N\n"
    "ATOM      2  CA  MET A   1      -8.608   3.135  -1.618  1.00 87.10           C\n"
    "ATOM      3  N   ALA A   2      -7.500   2.000  -1.000  1.00 90.00           N\n"
)


def test_extract_pdb_from_zip_and_raw():
    # Raw PDB passes through.
    assert tamarind._extract_pdb(b"ATOM...", _PDB) == _PDB
    # Zip is unpacked and the ranked PDB chosen.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("job/config.json", "{}")
        z.writestr("job/relaxed_rank_001_model.pdb", _PDB)
    out = tamarind._extract_pdb(buf.getvalue(), "")
    assert out and out.startswith("ATOM")
    # Non-PDB text yields nothing (never fabricated).
    assert tamarind._extract_pdb(b"nope", "some html") is None


def test_job_record_lookup_reads_resulturl():
    payload = {
        "jobs": [
            {"JobName": "achilles_af_marr", "JobStatus": "Complete",
             "resultUrl": "https://tamarind-data.s3.amazonaws.com/x/result-marr.zip?sig=1"}
        ],
        "statuses": {"Complete": 1},
    }
    rec = tamarind._job_record(payload, "achilles_af_marr")
    assert rec and rec["JobStatus"] == "Complete"
    assert rec["resultUrl"].endswith("result-marr.zip?sig=1")
    assert tamarind._job_record({"jobs": []}, "nope") is None
    # A single unlabeled record (jobName-filtered response) is still returned.
    assert tamarind._job_record({"jobs": [{"JobStatus": "Running"}]}, "whatever")["JobStatus"] == "Running"


def test_plddt_and_residue_count():
    assert tamarind.plddt_from_pdb(_PDB) == round((88.50 + 87.10 + 90.00) / 3, 1)
    assert tamarind.residue_count_from_pdb(_PDB) == 2  # MET A1, ALA A2
    assert tamarind.plddt_from_pdb("no atoms here") is None
