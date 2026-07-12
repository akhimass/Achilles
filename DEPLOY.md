# Deploying Achilles

The backend + Postgres go on **Railway**; the frontend goes on **Vercel**. The
deployed app runs on the **public reproduction path only** (PubMLST + committed public
caches) — BurkData is never deployed. Every default endpoint is deterministic/cached,
so `ANTHROPIC_API_KEY` is **optional** (only the opt-in `?narrate=true` path uses it).

You run the Railway steps (your token can reach Railway; my build sandbox can't).
Once you paste me the backend URL, I deploy the frontend to Vercel pointed at it.

---

## 1. Postgres + pgvector on Railway

1. Railway → **New Project** → **Deploy PostgreSQL**.
2. Open the Postgres service → **Settings → Source Image** and set it to
   `pgvector/pgvector:pg16` (this ships the `vector` extension `schema.sql` needs),
   then redeploy the database. (Railway's default Postgres image lacks pgvector.)
3. Copy the **public** connection string from the Postgres service **Variables** tab
   (`DATABASE_PUBLIC_URL`, looks like `postgresql://user:pass@host:port/railway`).

## 2. Apply the schema and seed the PUBLIC graph (from your machine)

From the repo root (`switchback/`), with the public URL from step 1:

```bash
# a) create the tables (psql understands the plain postgresql:// scheme)
psql "postgresql://user:pass@HOST:PORT/railway" -f db/schema.sql

# b) seed ONLY public data (PubMLST + committed caches). Note the +asyncpg scheme
#    and ACHILLES_SEED_PUBLIC=1 — this guarantees no BurkData is loaded.
cd backend
pip install -e .            # first time only (installs the app + deps)
DATABASE_URL="postgresql+asyncpg://user:pass@HOST:PORT/railway" \
  ACHILLES_SEED_PUBLIC=1 python -m app.ingestion.seed --public
```

Expected seed output (public path): ~70 PubMLST strains, ~490 MLST variants + 5
reference genes, ~96 papers / ~61 evidence edges, 5 ranked targets, and
`seed(collateral): skipped` (collateral derives from private BurkData → the cycling
panel shows its honest empty state on the public deployment).

## 3. Deploy the backend service on Railway

1. Same project → **New** → **GitHub Repo** → `akhimass/Achilles`.
2. Service **Settings**:
   - **Root Directory**: `backend`  ← important (the Dockerfile builds from here)
   - Build uses `backend/Dockerfile` automatically; `backend/railway.toml` sets the
     start command and `/health` healthcheck.
3. Service **Variables**:
   - `DATABASE_URL` = `postgresql+asyncpg://` + the Postgres service's **internal**
     credentials, e.g.
     `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}`
     (internal networking needs no SSL). The `+asyncpg` prefix is required.
   - `ALLOWED_ORIGINS` = `*` for now; tighten to the Vercel URL after step 5.
   - *(optional)* `ANTHROPIC_API_KEY` = `sk-ant-…` — only for the `?narrate=true` path.
   - `PORT` is injected by Railway automatically; the start command honors it.
4. Deploy. Railway gives the service a public domain (**Settings → Networking →
   Generate Domain**), e.g. `https://achilles-backend-production.up.railway.app`.

## 4. Verify the backend over the public internet

```bash
curl https://<your-backend>.up.railway.app/health
# {"status":"ok","service":"achilles","version":"0.1.0"}

curl "https://<your-backend>.up.railway.app/api/graph/lineage?organism=Burkholderia%20multivorans" | head -c 400
# {"nodes":[...],"edges":[...]}  ← real seeded data
```

## 5. Frontend on Vercel

**Paste me the backend URL** and I deploy the Next.js app to Vercel with
`NEXT_PUBLIC_API_BASE=<backend URL>` baked in at build (that env var is inlined at
build time, which is why I need the real URL first). Then set the backend's
`ALLOWED_ORIGINS` to the returned Vercel URL and redeploy the backend once.

---

### CLI alternative (steps 1 + 3)

```bash
npm i -g @railway/cli
export RAILWAY_TOKEN=<your token>     # project token from Railway → project → Settings → Tokens
railway link                          # select the project
railway up --service <backend>        # deploy from ./backend (set root dir first)
railway variables --service <backend> --set 'DATABASE_URL=postgresql+asyncpg://…' --set 'ALLOWED_ORIGINS=*'
```

If `CREATE EXTENSION vector` errors, the Postgres image isn't pgvector — redo step 1.2.

---

## Seeding a managed Postgres (Supabase) without a direct connection

When the app's environment can't open a Postgres wire connection to the managed DB
(sandbox egress, etc.), seed with a generated SQL bundle instead of live asyncpg:

```bash
# 1) create the schema (pgvector + tables) and 2) load the PUBLIC graph
make seed-sql                                   # writes achilles_public_seed.sql (public only)
psql "$SUPABASE_DATABASE_URL" -f db/schema.sql -f achilles_public_seed.sql
```

The bundle is deterministic and idempotent (ON CONFLICT upserts), PUBLIC-only (PubMLST
+ committed caches — never BurkData), and loads ~12 genes, 70 strains, 490 variants,
96 papers, 61 evidence edges, 5 ranked targets. Point the backend at it with
`DATABASE_URL=postgresql+asyncpg://…` (Supabase → Connect → SQLAlchemy/asyncpg URI;
append `?prepared_statement_cache_size=0` if using the transaction pooler).
