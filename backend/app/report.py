"""Downloadable auditable report — a keepable, re-verifiable receipt.

Renders the self-validation result + its hash-chained ledger into one self-contained HTML
file (inline CSS, no external assets) that a researcher can save, share, or archive. The
report embeds the ledger as JSON and states exactly how to re-verify it (POST it back to
`/api/audit/verify`, or re-walk the sha256 chain offline). Pure string building —
unit-testable, and the same ledger the console shows.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _verdict_class(status: str) -> str:
    if status in ("recovered",):
        return "ok"
    if status == "refused":
        return "ok"
    if status in ("fabricated", "weakly_asserted"):
        return "bad"
    return "muted"


def validation_report_html(
    report: dict, ledger: list[dict], head: str, organism: str = ""
) -> str:
    """Build a self-contained audit report. Pure."""
    m = report.get("metrics", {})
    items = report.get("items", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    controls = (m.get("positives") or 0) + (m.get("negatives") or 0)

    rows = []
    for it in items:
        prov = it.get("provenance") or {}
        cite = prov.get("acc") or prov.get("pmid") or "—"
        url = prov.get("ref_url") or prov.get("pubmed_url")
        cite_html = f'<a href="{_esc(url)}">{_esc(cite)}</a>' if url else _esc(cite)
        rows.append(
            f"<tr><td>{_esc(it.get('gene'))}</td>"
            f"<td>{_esc(it.get('relation'))}</td>"
            f"<td>{_esc(', '.join(it.get('target_terms', [])))}</td>"
            f"<td class='{_verdict_class(it.get('status',''))}'>{_esc(it.get('status'))}</td>"
            f"<td class='mono'>{cite_html}</td></tr>"
        )

    # XSS-safe embedding of JSON inside a <script> tag: neutralize any "<" so a value
    # like "</script>" can't break out (and no literal "<script>" survives).
    ledger_json = json.dumps({"ledger": ledger}, separators=(",", ":")).replace("<", "\\u003c")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Achilles — audit report ({_esc(organism)})</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#060d0a; color:#e9f1ed;
    font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:32px 22px 60px; }}
  h1 {{ font-size:22px; margin:0 0 2px; letter-spacing:-.01em; }}
  .sub {{ color:#7fa08f; font-size:12.5px; margin:0 0 20px; }}
  .accent {{ color:#52e2ac; }} .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  .metrics {{ display:flex; flex-wrap:wrap; gap:14px; margin:16px 0 20px; }}
  .metric {{ flex:1; min-width:150px; border:1px solid #1c2f25; border-radius:12px; padding:12px 14px; background:#0d1712; }}
  .metric .v {{ font-family:ui-monospace,monospace; font-size:22px; color:#52e2ac; }}
  .metric .l {{ font-size:11px; color:#7fa08f; text-transform:uppercase; letter-spacing:.04em; }}
  .fingerprint {{ border:1px solid #1c2f25; border-radius:12px; padding:12px 14px; background:#0d1712; margin-bottom:20px; }}
  .fingerprint code {{ font-family:ui-monospace,monospace; font-size:12px; word-break:break-all; color:#e9f1ed; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th, td {{ text-align:left; padding:7px 8px; border-bottom:1px solid #14231b; }}
  th {{ color:#7fa08f; font-weight:600; text-transform:uppercase; font-size:10.5px; letter-spacing:.04em; }}
  td.ok {{ color:#52e2ac; }} td.bad {{ color:#f87171; }} td.muted {{ color:#98a2b3; }}
  a {{ color:#52e2ac; }}
  .note {{ margin-top:22px; border:1px solid #1c2f25; border-radius:12px; padding:14px 16px; background:#0d1712; font-size:12.5px; color:#9fb2a8; }}
  pre {{ background:#081210; border:1px solid #14231b; border-radius:8px; padding:10px; overflow:auto; font-size:11.5px; color:#cfe; }}
  .foot {{ margin-top:26px; color:#5c7466; font-size:11px; }}
</style></head>
<body><div class="wrap">
  <h1>Achilles — <span class="accent">audit report</span></h1>
  <p class="sub">Self-validation of the grounded evidence graph · {_esc(organism)} · generated {now}</p>

  <div class="metrics">
    <div class="metric"><div class="v">{_esc(m.get('recovered'))}/{_esc(m.get('positives'))}</div><div class="l">Known biology recovered</div></div>
    <div class="metric"><div class="v">{_esc(m.get('refused'))}/{_esc(m.get('negatives'))}</div><div class="l">Adversarial claims refused</div></div>
    <div class="metric"><div class="v">{_esc(m.get('fabricated'))}</div><div class="l">Fabricated (must be 0)</div></div>
    <div class="metric"><div class="v">{controls}</div><div class="l">Public controls</div></div>
  </div>

  <div class="fingerprint">
    <div class="l" style="color:#7fa08f;font-size:11px;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">sha256 hash-chain head</div>
    <code>{_esc(head)}</code>
  </div>

  <table><thead><tr><th>Gene</th><th>Relation</th><th>Target</th><th>Verdict</th><th>Citation</th></tr></thead>
  <tbody>{''.join(rows)}</tbody></table>

  <div class="note">
    <b class="accent">How to re-verify this report.</b> Every verdict above is an entry in a
    sha256 hash-chain; the head fingerprint is a function of all of them, so any edit changes
    it. To confirm this report was not altered, POST the embedded ledger back to the live API:
    <pre>curl -s -X POST {'{ACHILLES_API_BASE}'}/api/audit/verify \\
  -H 'content-type: application/json' \\
  --data-binary @ledger.json    # =&gt; {{"valid": true, "head": "…"}}</pre>
    The ledger is embedded below (and the deterministic verdicts mean the head is stable —
    same grounded graph, same fingerprint).
    <script type="application/json" id="achilles-ledger">{ledger_json}</script>
  </div>

  <div class="foot">Achilles · deterministic core · provenance on every edge · MIT ·
  research decision-support, not medical advice.</div>
</div></body></html>
"""
