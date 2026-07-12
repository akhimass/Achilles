# Achilles on Supabase

A turnkey Postgres+pgvector database for Achilles. Everything here is **public data
only** — `seed.sql` is generated from `export_seed_sql.py` (PubMLST + committed
literature/reference caches). **BurkData is never included** and stays local.

- `migrations/20260101000000_init.sql` — the schema (`db/schema.sql`): strains, genes,
  variants, papers (pgvector), evidence_edges, targets, collateral_sensitivity.
- `seed.sql` — the public evidence graph as idempotent `INSERT`s (12 genes, 70 strains,
  490 variants, 96 papers, 61 edges, 5 targets). Regenerate with `make supabase-bundle`.

## Option A — Supabase CLI (recommended)

```bash
supabase link --project-ref <your-project-ref>   # from the Supabase dashboard
supabase db push                                  # applies migrations/
psql "$SUPABASE_DB_URL" -f seed.sql               # loads the public graph
# (or `supabase db reset` locally — runs migrations/ then seed.sql automatically)
```

## Option B — psql only (no CLI)

```bash
psql "$SUPABASE_DB_URL" -f migrations/20260101000000_init.sql
psql "$SUPABASE_DB_URL" -f seed.sql
```

`SUPABASE_DB_URL` is the **direct/session** connection string (Dashboard → Project
Settings → Database → *Connection string* → URI). Use the session-mode/direct URI for
migrations, not the transaction pooler.

## Point the backend at Supabase

The API uses an **asyncpg** URL. Convert the Supabase URI:

```
postgresql://postgres:<pwd>@db.<ref>.supabase.co:5432/postgres
        ↓
DATABASE_URL=postgresql+asyncpg://postgres:<pwd>@db.<ref>.supabase.co:5432/postgres
```

Set `DATABASE_URL` in `backend/.env` (or the deploy env) and the app reads the graph
straight from Supabase — no local Postgres needed.

## Automated provisioning (Supabase MCP connector)

The Supabase MCP connector can create the project and apply migrations for you, but it
must be **authorized first** (it can't run OAuth from a non-interactive/sandboxed
session). Authorize it via your claude.ai connector settings, or `claude mcp` / `/mcp`
in an interactive Claude Code session. Until then, use Option A or B above.
