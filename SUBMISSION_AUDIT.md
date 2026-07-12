# Achilles — submission readiness & competitive audit

_Snapshot taken against the live deployment + Supabase + the hackathon Discord field._

## Verdict

**The product is ready. The submission is not — yet.** Three things stand between you and
a clean submission, none of them "build more features":

1. **Push the last 5 local commits** so the live site matches your best build.
2. **Record the demo video** (runbook below).
3. **Write the ~200-word submission blurb** (draft below).

Everything the judges will actually score — a working, grounded, verifiable pipeline on
real data — already exists and is (mostly) live.

## Live state (verified, not assumed)

- **Database (Supabase): seeded.** 70 strains, 12 genes, 61 evidence edges (44 grounded),
  96 papers, 5 ranked targets, 10 cited collateral-sensitivity pairs.
- **Backend (Railway): up and correct.** `/api/validation` returns 9/9 recovered, 4/4
  refused, **0 fabricated**, every claim cited to CARD + PMID. The prove-it engine is live.
- **Frontend (Vercel): READY but 5 commits behind** (`282b25a`). Live today: prove-it,
  red-team, retrodiction, docking, cycling, targets, lineage, structures. **Not yet live:**
  Ask Achilles, the persona sidebar, the blank/demo-toggle reframe, the generic landing,
  and the `/api/domains` registry (confirmed 404 on live).

**Action:** push `a46093f` (+ its 4 ancestors) → Vercel & Railway auto-redeploy → live == HEAD.

## Where we stand vs the Discord field

The strongest competitors are all circling **verifiability** — which is exactly Achilles'
thesis, and the judges (Gladstone / Katie Pollard, Anthropic's Claude-for-Life-Sciences)
are computational-biology-literate and will reward rigor and reproducibility.

| Competitor (Discord) | Their edge | How Achilles compares |
|---|---|---|
| **Ubaid — enhancer checker** | 0.80 cross-lab AUROC on 93,435 independent designs; flags grounded in TF motifs | Most quantitatively rigorous rival. Achilles' validation is a *harder property* (recovers known + refuses false + **anticipates future** via time-split retrodiction, 0 fabrications) but on small N (13 controls). **Lead with the property and the live red-team, not the raw N.** |
| **TrialBridge (Angelo)** — trial feasibility from RWE | "provable vs not-evaluable per criterion" | Same provability discipline, different domain. Achilles' new domain-agnostic framing makes this an *adjacent* use case, not a competitor. |
| **Phebe — PKU / decentralized science** | "make non-verifiable claims verifiable by design" | Philosophically identical thesis. Achilles is the general-purpose engine for that idea. |
| **Steven — neuroimaging biomarkers** | Alzheimer's imaging | Different domain; no overlap. |
| **Many "wrapper" apps** (self-admitted) | thin LLM UI | Achilles is decisively not a wrapper: deterministic core + provenance graph + real AlphaFold/CARD/PubMLST/ChEMBL integrations + a test suite. |

### Where we win
- **Verifiability is interactive and live**, not a claimed metric. A judge can *inject a
  false claim and watch it refuse* (red-team) and *slide a cutoff and watch it anticipate a
  later paper* (retrodiction). Almost no one else lets you break their tool on stage.
- **A complete grounded pipeline**, not a slice: strain → reversible target → structure →
  cited treatment hypothesis, every edge with provenance.
- **Reproducible & open**: public data, offline seed, MIT, deterministic core — reads as
  real science infrastructure.
- **Domain-agnostic** now: AMR is the worked example, not the ceiling.

### Where we're exposed (and the fix)
- **Validation N is small.** Fix: frame around the *property* + interactivity; mention
  retrodiction's foresight; don't get into an AUROC arms race you'll lose on raw count.
- **The app does a lot** — easy to lose a judge. Fix: the tight runbook below; resist
  showing every panel.
- **Second domain is a scaffold.** Fix: say exactly that — "domain-agnostic pipeline,
  proven on AMR, wired for the next domain" — never imply a populated second disease.
- **Clinical over-claim risk.** Already handled: cycling is labelled a research hypothesis
  everywhere. Keep that line in the voiceover.

## Demo runbook (~3 min, the money moments)

Record from **HEAD** (push first) or localhost so Ask + the reframe are present.

1. **Open blank (10s).** "Achilles is a domain-agnostic, evidence-grounded discovery
   console — bring your data, every claim stays cited." Toggle **Demo data → AMR**.
2. **Prove it (35s).** Validation panel: 9/9 recovered, 4/4 refused, **0 fabricated**, each
   cited. "Most tools claim accuracy; this one proves it."
3. **Red-team, live (30s).** Type a false claim (`MarR → vancomycin`) → **refused**. Then a
   true one (`MarR → ciprofloxacin`) → **supported, cited**. This is the emotional peak.
4. **Retrodiction (30s).** Slide cutoff to 2019 → AraC/MarA **anticipates** its 2020
   tigecycline confirmation, 0 false calls. "Not just recall — foresight."
5. **Ask, grounded (25s).** Ask "what re-sensitizes after meropenem?" → cited answer + the
   **intent-routed cycle** appears with a PMID. "It answers only from cited evidence, or
   refuses."
6. **Target → structure → docking (25s).** Top target, AlphaFold fold (Tamarind), the cited
   efflux inhibitor docked. "Tractability to structure to a cited molecule."
7. **Generalize (15s).** "Bring your own data" / Try another organism → same core, different
   organism. Close on: deterministic core, provenance on every edge, reproducible from
   public data, MIT.

## Pre-submission checklist

- [ ] Push last 5 commits; confirm live `/api/domains` responds and Ask appears.
- [ ] Re-check live `/api/validation` (0 fabricated) after redeploy.
- [ ] Record 3-min demo per runbook.
- [ ] Submission blurb (draft below) + repo link + live link.
- [ ] Optional: run `make fold-targets` / `make dock-targets` with a Tamarind key so the
      docking pose is populated, not "ready to dock."

## Draft submission blurb

> **Achilles** is an evidence-grounded discovery console. Point it at your data and it
> builds a provenance-checked graph where every claim carries a citation — a deterministic
> core does the math, and the model only reads, retrieves, and cites. Its edge is
> verifiability you can break live: it recovers known biology (9/9), refuses planted false
> claims (0 fabrications), and on a time-split hold-out **anticipates** findings before the
> confirming paper. Demonstrated end-to-end on antimicrobial resistance — reversible targets
> from collateral sensitivity, AlphaFold structures, a cited antibiotic-cycling hypothesis —
> the pipeline is domain-agnostic and reproducible from public data. MIT.
