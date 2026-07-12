FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libz-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY . .
# Bundle the PUBLIC committed data caches the runtime reads (benchmark ground-truth for
# validation/retrodiction, docking ligands, folded structures, PubMLST snapshot) at the
# repo-root-relative path the app resolves to in-container (parents[3] -> /data/demo).
# PUBLIC-ONLY by construction — BurkData is never staged into deploy_assets, so it can
# never reach the image.
COPY deploy_assets/demo/ /data/demo/
# Honor $PORT (Railway and most PaaS inject it); default 8000 for local `docker run`.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
