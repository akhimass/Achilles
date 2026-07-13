# Private saved projects — auth + owner-scoped isolation

This is the multi-tenant step: let a signed-in user **privately** save and reload their own
work, with no one else (and no operator) able to read it. The design keeps the current
privacy guarantee intact.

## The key design decision

**User data goes browser → Supabase (Auth + RLS). It never passes through the FastAPI
backend or the language model.**

Why: the backend connects to Postgres as the `postgres` role, which **bypasses** Row-Level
Security. So routing user data through the backend would defeat RLS unless we re-implemented
per-user checks in code. Instead we keep user data on the path where RLS *is* the gate — the
Supabase client, authenticated with the user's session. The backend stays stateless and
public (the "never stored, never sent to the model" guarantee from `PRIVACY.md` is
preserved), and isolation is enforced declaratively by the database.

```
BYO upload  ──▶  FastAPI /api/ingest/upload  ──▶  deterministic lineage (in memory)  ──▶  back to the browser
(stateless, no DB, no model)                                                              │
                                                          user clicks "Save to my workspace"│
                                                                                           ▼
                                          Supabase client (user's JWT)  ──▶  saved_projects  [RLS: auth.uid() = owner]
```

## What's already done

- **Migration**: `supabase/migrations/20260102000000_saved_projects.sql` — the
  `saved_projects` table + owner-scoped RLS (select/insert/update/delete all gated on
  `auth.uid() = owner`; no public/anon policy, so cross-user reads are impossible). Reviewed
  and safe to apply.

## Finish steps (needs Supabase keys + a live test)

1. **Apply the migration — apply ONLY this file, do not `supabase db push`.**
   The live database was built from `db/schema.sql` + `supabase/seed.sql`, **not**
   migration-managed. `supabase db push` would also try to apply
   `20260101000000_init.sql`, which collides with the already-live schema. Apply just the
   saved-projects file directly:
   ```bash
   psql "$SUPABASE_DB_URL" -f supabase/migrations/20260102000000_saved_projects.sql
   ```
   The file is idempotent (guarded `create table … if not exists` + `drop policy if exists`
   before each policy), so re-running it is safe. Only reach for `supabase db push` if/when
   this project is fully migration-managed.
2. **Enable Auth** in the Supabase dashboard (magic link and/or Google). No backend change.
3. **Frontend deps + env.**
   ```bash
   cd frontend && npm install @supabase/supabase-js
   # .env.local
   NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>   # safe to ship — RLS is the gate
   ```
4. **Add the client** — `frontend/src/lib/supabase.ts`:
   ```ts
   import { createClient } from "@supabase/supabase-js";
   export const supabase = createClient(
     process.env.NEXT_PUBLIC_SUPABASE_URL!,
     process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
   );
   ```
5. **Save / load / delete** (RLS-enforced; `owner` is auto-checked against the session):
   ```ts
   // save the BYO result the user is looking at
   await supabase.from("saved_projects").insert({
     owner: (await supabase.auth.getUser()).data.user!.id,
     name, kind: "lineage", payload,
   });
   // list only MY projects (RLS returns nothing for anyone else)
   const { data } = await supabase.from("saved_projects")
     .select("id,name,created_at").order("created_at", { ascending: false });
   // delete one of mine
   await supabase.from("saved_projects").delete().eq("id", id);
   ```
   Put a sign-in button + "Save to my workspace" on the BYO result, and a "My projects"
   list. A self-contained `/workspace` route keeps this off the demo path.
6. **Security review before shipping.** Sign in as two different users; confirm user B
   cannot see or delete user A's rows (RLS should return zero rows / block the write).
   Confirm the anon key alone (no session) can read nothing from `saved_projects`.

## What stays true

- The default remains **ephemeral**: nothing is saved unless the user signs in and clicks
  save. BYO stays stateless on the backend.
- Saved data is **owner-only** by construction (RLS), separate from the public demo tables,
  encrypted at rest, deletable, and never sent to the model.
