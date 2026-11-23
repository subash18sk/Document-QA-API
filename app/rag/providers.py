"""
Builds the configured embedder and answerer once, and exposes them as FastAPI dependencies.

Routes receive them via Depends(...), so tests can swap in fakes with app.dependency_overrides
without touching any route code.
"""
from functools import lru_cache

from app.config import settings
from app.rag.answer import ExtractiveAnswerer, OpenAICompatLLM
from app.rag.embeddings import HashEmbedder, OpenAICompatEmbedder


@lru_cache
def get_embedder():
    if settings.embeddings_provider == "openai":
        return OpenAICompatEmbedder(
            base_url=settings.embeddings_base_url or settings.llm_base_url,
            api_key=settings.embeddings_api_key or settings.llm_api_key,
            model=settings.embeddings_model,
            timeout=settings.llm_timeout_seconds,
        )
    return HashEmbedder(settings.hash_dimensions)


@lru_cache
def get_answerer():
    if settings.llm_provider == "openai":
        return OpenAICompatLLM(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
    return ExtractiveAnswerer()
