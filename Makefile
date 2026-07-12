.PHONY: dev db backend frontend seed seed-public test fmt

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

test:
	cd backend && pytest -q

fmt:
	cd backend && ruff check --fix . && black .
