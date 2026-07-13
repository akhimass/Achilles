# Data privacy

Achilles is built so a researcher can bring sensitive material without it leaking. This
documents what actually happens to data you put in — verifiable in the code, not a promise.

## Today: bring-your-own data is private by construction

When you upload a genotype CSV in **Bring your own data** (`POST /api/ingest/upload`):

- It is parsed **in memory**, the lineage + flipper graph is computed, and the result is
  returned in the response. Then it is **gone**.
- **No database write.** The upload path (`backend/app/routers/ingest.py`,
  `backend/app/ingestion/upload.py`) imports no DB layer and runs no `INSERT` — it is
  stateless.
- **Never sent to the language model.** The upload path imports no AI layer. The
  deterministic core (MST lineage + flipper detection) is plain Python; the model is not in
  the loop for your data.
- **Not logged.** The request body is not written to logs.
- Transport is **HTTPS** (TLS in transit).

The only thing persisted server-side is the **public demo graph** (Burkholderia, from
public sources). No user upload is stored in it.

## What would touch persistence or the model — and how it stays private

The stateless model above is the default and the safest option. Some product features need
more; each has a clear privacy rule.

### Saved projects / multi-session (requires persistence)
- **Auth + per-user isolation.** Store user data in owner-scoped rows and enforce Postgres
  **Row-Level Security** keyed to the authenticated user (`owner = auth.uid()`).
- **Important:** the public demo tables use a *public-read* RLS policy — correct for public
  data, but user data must **never** live in those tables. User data goes in separate,
  owner-scoped tables/rows whose RLS grants access only to the owner. Public-read and
  user-private data are kept apart by construction.
- **Encryption at rest** (managed Postgres / Supabase) + TLS in transit.
- **Deletion / erasure.** A user can delete their data; deletes are hard, not soft.
- **No third-party mixing.** User data is never merged into the shared public graph.

### Grounding a user's own literature (would use the model)
- Extraction sends abstract text to the Anthropic API. Anthropic does **not** train on API
  data by default — but for unpublished or sensitive text, offer one of:
  1. a **deterministic-only** path (lineage/flippers, no model call) for sensitive uploads;
  2. **bring-your-own Anthropic key**, so the call runs under the user's own account/terms;
  3. explicit, per-upload consent before any text leaves the browser.
- Never send **patient-identifiable data (PHI)** to any external API without a Business
  Associate Agreement in place.

### Clinical / PHI
Achilles is **research decision-support, not a diagnostic device**, and is **not** a
HIPAA-covered service. Do not upload patient-identifiable data. If a clinical deployment is
needed, it requires a proper compliance path (BAA with Anthropic + subprocessors, access
controls, audit logging, and a formal DPIA).

## Why this fits the product

The whole thesis is trust: cite or refuse, deterministic core, reproducible. "Your data
never leaves your control unless you opt in" is the same value applied to privacy — and
it's a real differentiator. The default is **ephemeral and local-first**; persistence and
model-grounding of *your* data are opt-in, isolated, and deletable.

## Roadmap to a private multi-tenant product

1. Keep BYO ephemeral as the default (done).
2. Auth (Supabase Auth) + owner-scoped RLS for saved projects; user data in its own
   namespace, never the public tables.
3. A "sensitive mode" toggle: deterministic-only, or bring-your-own model key.
4. Per-user delete + data-export; scrub any request logging.
5. If clinical: BAA, encryption review, audit logging, DPIA.
