# Achilles — demo voiceover (~3.75 min, one take)

**Record at:** https://achilles-science.vercel.app  ·  have a second tab on `/explore`.
Every beat below is verified against the live site at submission. Read the **SAY** lines
straight; do the **[DO]** actions as you talk. Timings are cumulative.

Reality check baked into the script: the docking **pose is not computed** — the inhibitor
is cited and "ready to dock," and the script says exactly that. Cycling is a **research
hypothesis**, said out loud.

---

### 0:00 — 0:18 · Open blank (the product, not the domain)
**[DO]** Land on `/explore` — it's blank, "No dataset loaded."
**SAY:** "This is Achilles — an evidence-grounded discovery console. It opens empty:
bring your own data and it builds a graph where every claim carries a citation. Nothing is
asserted without a source. Let me load our worked example."
**[DO]** Click the **Demo data** toggle (top right) → it flips to the AMR dataset.

### 0:18 — 0:56 · Prove it (the thing a search box can't do)
**[DO]** Scroll to the **Prove it** chapter.
**SAY:** "Most tools claim accuracy. Achilles proves it, live, against 29 independent public
controls. It recovers twelve of twelve known resistance relationships — each cited to CARD
and a PubMed ID — refuses all seventeen claims in an adversarial battery of plausible
falsehoods, and fabricates nothing. Zero. And the whole result is written to a
tamper-evident, hash-chained ledger — you can re-verify it yourself at `/api/audit`. Numbers
you can't fake, receipts you can re-check."

### 0:52 — 1:24 · Red-team it (let the judge break it)
**[DO]** In the red-team box, type gene **MarR**, target **vancomycin** → **Test claim**.
**SAY:** "Watch — I'll inject a false claim. MarR confers vancomycin resistance."
**[DO]** It returns **refused**.
**SAY:** "Refused — no grounded evidence, so it won't fabricate one. Now a true one."
**[DO]** Type **MarR** / **ciprofloxacin** → **Test claim** → **supported**, with citation.
**SAY:** "Supported — and it shows you the receipt. You can't talk it into a claim it
can't ground."

### 1:24 — 1:54 · Retrodiction (recall is table stakes; this is foresight)
**[DO]** Go to the retrodiction slider; drag the cutoff to **2019**.
**SAY:** "Recovering what's known is table stakes. This is harder: freeze the evidence at
2019 and hide everything after. AraC/MarA was already grounded as a multidrug-efflux driver
by 2013 — so the frozen graph anticipates its 2020 tigecycline-resistance paper it never
saw. Foresight, not hindsight — and zero false calls."

### 1:54 — 2:20 · Ask it (grounded answers or none)
**[DO]** Scroll to **Ask Achilles**; set the lens to **Physician**. Type
**"what re-sensitizes after meropenem"** → Ask.
**SAY:** "Ask in plain language. The answer is built only from cited evidence — here, each
claim numbered and linked — and because I'm asking as a clinician, it flags that this is
research evidence, not medical advice. If nothing in the graph supports a question, it
refuses instead of guessing."

### 2:20 — 2:44 · Target → structure → inhibitor
**[DO]** Open **Target identification**; show the top ranked target and its AlphaFold fold;
scroll to docking.
**SAY:** "From evidence to a target with a deterministic score, to its AlphaFold structure,
to a known efflux inhibitor — CCCP — traced to a CARD accession and ready to dock into that
structure. Cited chemistry, not an invented molecule."

### 2:44 — 3:06 · The bridge (bench → bedside, same receipts)
**[DO]** Still on the selected target — click **Clinical translation for {gene} →** (jumps
to the Treatment chapter's bridge, tied to that gene).
**SAY:** "One click turns that bench finding into a physician-facing summary — same grounded
evidence, clinician framing, and flagged in bold as research evidence, not medical advice.
The researcher and the physician read the same receipts. That handoff is the product."

### 3:06 — 3:22 · It's not an AMR app (close)
**[DO]** Go to **Your data**; hover **Try another organism**; then gesture to the toggle.
**SAY:** "And none of this is bacteria-specific. Drop any organism's data and the same
deterministic core runs. A deterministic core, provenance on every edge, reproducible from
public data, MIT. That's Achilles."

### 3:22 — 3:44 · And Claude can call it (Claude Code / Cowork)
**[DO]** Switch to a Claude Code or Cowork window with the Achilles MCP connected. Type:
*"Is MarR → ciprofloxacin grounded, and what re-sensitizes after meropenem, as a physician?"*
**SAY:** "Everything you just saw is also a tool. Here's Claude — in Cowork — calling
Achilles: it grounds the claim to a CARD accession, and answers the treatment question only
from cited evidence, flagged research-not-advice. Claude doing trustworthy science through a
tool that can't hallucinate. That's the platform."
_(No MCP set up on camera? Show the `/mcp` page instead and read the same line.)_

---

## If you have 60 seconds (cut-down)
Blank → toggle demo → **Prove it (12/12 recovered · 17/17 refused · 0 fabricated, on a
tamper-evident ledger)** → **red-team refuse+support** → **bridge** (bench→bedside, same
receipts) → one line: "grounded or it refuses, reproducible from public data." Stop there —
the red-team and the ledger are the moments that land.

## Do-not-say list
- Don't say "docked pose" — say "ready to dock."
- Don't say "predicts treatment" — say "a research hypothesis."
- Don't imply the bridge is medical advice — it's the same **research** evidence, clinician-
  framed, and says so on screen.
- Lead with the *property* (recover known biology **and** refuse a large adversarial
  battery, verifiably) — the 29-control size and the re-verifiable ledger back it up.
