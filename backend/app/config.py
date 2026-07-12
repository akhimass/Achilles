"""Application settings, loaded from environment / .env.

Model IDs are config-driven on purpose. No module should hard-code a model
string — read `settings.model_extract` / `settings.model_reason` instead, so the
whole AI layer can be re-pointed from one place.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://switchback:switchback@localhost:5432/switchback"

    # Anthropic
    anthropic_api_key: str = ""
    # Current defaults (Jul 2026). Sonnet 5 for high-volume extraction; Opus 4.8 for
    # the harder ranking/narration. Swap here, not in modules.
    model_extract: str = "claude-sonnet-5"
    model_reason: str = "claude-opus-4-8"
    embedding_dim: int = 1024

    # External public data sources
    europepmc_base: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    card_base: str = "https://card.mcmaster.ca"
    # CARD's Antibiotic Resistance Ontology (ARO) is served publicly by EBI OLS,
    # which grounding queries for ARO accessions.
    ols_base: str = "https://www.ebi.ac.uk/ols4/api"
    uniprot_base: str = "https://rest.uniprot.org"
    # ChEMBL public bioactivity API — target tractability (known inhibitors / drugs).
    chembl_base: str = "https://www.ebi.ac.uk/chembl/api/data"
    bvbrc_base: str = "https://www.bv-brc.org/api"
    ncbi_eutils_base: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Tamarind Bio — AlphaFold structure prediction (AI/ML). Auth via x-api-key.
    tamarind_api_key: str = ""
    tamarind_base: str = "https://app.tamarind.bio/api/"
    tamarind_poll_max_seconds: int = 900
    tamarind_max_jobs: int = 25


settings = Settings()
