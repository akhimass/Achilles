"""Achilles API entrypoint.

Phase 0: health check + router wiring so the frontend can round-trip immediately.
Each router carries its own phase TODOs.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import graph, literature, structure, targets, treatment

app = FastAPI(title="Achilles API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router)
app.include_router(structure.router)
app.include_router(targets.router)
app.include_router(literature.router)
app.include_router(treatment.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "achilles", "version": "0.1.0"}
