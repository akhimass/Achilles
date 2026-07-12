# Achilles — demo voiceover (~3 min, one take)

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

### 0:18 — 0:52 · Prove it (the thing a search box can't do)
**[DO]** Scroll to the **Prove it** chapter.
**SAY:** "Most tools claim accuracy. Achilles proves it, live, against independent public
ground truth. It recovers nine of nine known resistance relationships — each cited to CARD
and a PubMed ID — refuses four of four planted false claims, and fabricates nothing. Zero.
That last number is the whole point."

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

### 2:44 — 3:00 · It's not an AMR app (close)
**[DO]** Go to **Your data**; hover **Try another organism**; then gesture to the toggle.
**SAY:** "And none of this is bacteria-specific. Drop any organism's data and the same
deterministic core runs. A deterministic core, provenance on every edge, reproducible from
public data, MIT. That's Achilles."

---

## If you have 60 seconds (cut-down)
Blank → toggle demo → **Prove it (9/9, 4/4, 0)** → **red-team refuse+support** → one line:
"grounded or it refuses, reproducible from public data." Stop there — the red-team is the
moment that lands.

## Do-not-say list
- Don't say "docked pose" — say "ready to dock."
- Don't say "predicts treatment" — say "a research hypothesis."
- Don't lead with the benchmark size (13 controls); lead with the *property* and the live
  red-team.
