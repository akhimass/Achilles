.PHONY: dev db backend frontend seed seed-public seed-sql supabase-bundle test fmt

db:            ## start Postgres+pgvector with schema loaded
	docker compose up -d db

backend:       ## run the FastAPI app (expects db up, .env present)
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:      ## run the Next.js app
	cd frontend && npm run dev

dev: db        ## bring up db, then run backend + frontend together
	@echo "db is up. In separate shells run: make backend  and  make frontend"

seed:          ## load the demo dataset (BurkData if present locally, else public)
	cd backend && python -m app.ingestion.seed

seed-public:   ## load ONLY public data (PubMLST + committed caches) — deploy/repro seed
	cd backend && python -m app.ingestion.seed --public

seed-sql:      ## export the PUBLIC seed as a SQL bundle (for Supabase/any Postgres)
	cd backend && python -m app.ingestion.export_seed_sql ../achilles_public_seed.sql

supabase-bundle: ## regenerate the committed Supabase project seed (public only)
	cd backend && python -m app.ingestion.export_seed_sql ../supabase/seed.sql

test:
	cd backend && pytest -q

fmt:
	cd backend && ruff check --fix . && black .

fold-targets:  ## fold every ranked target via Tamarind AlphaFold (needs TAMARIND_API_KEY)
	cd backend && python -m app.sources.fold_targets

dock-targets:  ## dock cited inhibitors + run ADMET via Tamarind (needs TAMARIND_API_KEY)
	cd backend && python -m app.sources.dock

fetch-domain:  ## fetch a domain's real PubMLST isolates → snapshot (e.g. DOMAIN=pseudomonas)
	cd backend && python -m app.sources.fetch_domain $(DOMAIN)
