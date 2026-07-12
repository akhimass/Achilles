# Pre-reviewed narration cache

The app serves **fixed, pre-reviewed, cited** LLM narration from this directory
instead of calling the model per visitor — faster, cheaper, reproducible, and
auditable. Read by `backend/app/ai/narration_cache.py`; written once by
`python -m app.sources.make_narration_snapshot` (needs `ANTHROPIC_API_KEY`).

When these files are empty (`{}`) — e.g. no key was available — the API falls back to
the **deterministic rationale** computed by `targets_shaping.py`. Narration is never
fabricated: no key ⇒ no cached entry ⇒ deterministic text.

## Files

- **`targets.json`** — map of `locus_tag → { narrative, citations, model, generated_at }`.
  Derives from the **public** literature corpus + public ChEMBL, so it is **safe to
  commit**. Served by `/api/targets` on the default (non-`narrate`) path, labelled
  `rationale_source: "cached"`.
- **`cycle.json`** — map of `organism → { summary, caveats, citations, model,
  generated_at }`. Cycle narration derives from the **private BurkData** collateral
  record, so it is **LOCAL-ONLY and never committed** (kept `{}` here). On the public
  deployment the cycle is empty anyway, so its narration is moot.
- **`trajectory.json`** — map of `organism|resisted → { summary, citations, model,
  generated_at }`. Trajectory narration describes what real BurkData lineages did after
  a resistance event, so it is likewise **LOCAL-ONLY and never committed** (kept `{}`).
  The public path has no trajectory, so the beat shows its honest empty state there.

Every cached entry carries the **same citations** the live path would produce, plus
the `model` id and `generated_at`, so a reviewer can audit exactly what created it.
The opt-in `?narrate=true` query still performs a live call and overrides the cache.
