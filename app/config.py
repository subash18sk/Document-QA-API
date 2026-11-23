"""
All settings, read from environment variables (or a local .env file).

Nothing secret lives in the code. Every AI provider is optional: with no keys set, the API
runs fully offline using a built-in embedder and an extractive answerer, which is also what
the test suite uses.
"""
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- database & auth -------------------------------------------------------------
    database_url: str = "sqlite:///./docqa.db"
    # Optional PostgreSQL schema. Lets several apps share one database (e.g. Render's single
    # free Postgres) while keeping their tables completely separate.
    database_schema: Optional[str] = None
    jwt_secret: str = "dev-only-insecure-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- uploads & chunking ------------------------------------------------------------
    max_upload_mb: float = 10
    chunk_words: int = 180          # words per chunk
    chunk_overlap: int = 40         # words shared between neighbouring chunks
    top_k: int = 4                  # chunks retrieved per question

    # --- embeddings --------------------------------------------------------------------
    # "hash": offline lexical embedder (no key, no download)
    # "openai": any OpenAI-compatible /embeddings endpoint (OpenAI, Gemini, Ollama, ...)
    embeddings_provider: Literal["hash", "openai"] = "hash"
    embeddings_model: str = "text-embedding-3-small"
    embeddings_base_url: Optional[str] = None   # defaults to llm_base_url
    embeddings_api_key: Optional[str] = None    # defaults to llm_api_key
    hash_dimensions: int = 1024

    # --- answer generation -------------------------------------------------------------
    # "extractive": quotes the best-matching sentences (no key needed)
    # "openai": any OpenAI-compatible /chat/completions endpoint (OpenAI, Groq, Gemini, Ollama, ...)
    llm_provider: Literal["extractive", "openai"] = "extractive"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: Optional[str] = None
    llm_timeout_seconds: float = 30

    # Below this cosine similarity, the best chunk is treated as "not in the document".
    # Leave unset to use a sensible default for the chosen embeddings provider.
    min_similarity: Optional[float] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise the database URL for SQLAlchemy.

        - Render/Heroku hand out 'postgres://', which SQLAlchemy doesn't accept.
        - The driver is named explicitly ('+psycopg2'): SQLAlchemy 2.1 changed its default
          PostgreSQL driver, so relying on the default would break when upgrading.
        """
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    @property
    def similarity_threshold(self) -> float:
        if self.min_similarity is not None:
            return self.min_similarity
        return 0.08 if self.embeddings_provider == "hash" else 0.30

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


settings = Settings()
