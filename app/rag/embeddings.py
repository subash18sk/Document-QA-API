"""
Step 3 of indexing: turn text into vectors ("embeddings") so similar meaning -> nearby vectors.

Two interchangeable embedders share one interface, `embed(texts) -> (n, d) float32 array`, with every
row L2-normalised so a dot product equals cosine similarity:

* HashEmbedder: offline and free. A "hashing trick" bag-of-words (unigrams + bigrams). It matches
  shared words, not synonyms, which is enough for demos and tests and needs no key or download.
* OpenAICompatEmbedder: calls any OpenAI-compatible /embeddings endpoint (OpenAI, Gemini's
  OpenAI-compatible API, Ollama, ...) for true semantic search.
"""
import hashlib
import math
from collections import Counter

import httpx
import numpy as np

from app.rag.text import tokenize


class ProviderError(RuntimeError):
    """An external AI provider failed or is misconfigured."""


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


class HashEmbedder:
    def __init__(self, dimensions: int = 1024):
        self.dimensions = dimensions
        self.name = f"hash-{dimensions}"

    def _bucket(self, feature: str) -> tuple[int, float]:
        # blake2b, not Python's hash(): the built-in is randomised per process, which would make
        # stored vectors unusable after a restart.
        h = int.from_bytes(hashlib.blake2b(feature.encode(), digest_size=8).digest(), "big")
        return h % self.dimensions, (1.0 if (h >> 63) & 1 else -1.0)

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = tokenize(text)
            feats = Counter(tokens)
            feats.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
            for feat, tf in feats.items():
                idx, sign = self._bucket(feat)
                out[row, idx] += sign * (1.0 + math.log(tf))
        return _normalise(out)


class OpenAICompatEmbedder:
    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float = 30,
                 client: httpx.Client | None = None, batch_size: int = 64):
        if not api_key:
            raise ProviderError("EMBEDDINGS_PROVIDER=openai needs an API key (EMBEDDINGS_API_KEY or LLM_API_KEY).")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = f"openai:{model}"
        self.batch_size = batch_size
        self.client = client or httpx.Client(timeout=timeout)
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                resp = self.client.post(f"{self.base_url}/embeddings", headers=self.headers,
                                        json={"model": self.model, "input": batch})
                resp.raise_for_status()
                data = sorted(resp.json()["data"], key=lambda d: d["index"])
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise ProviderError(f"Embedding request failed: {exc}") from exc
            rows.extend(d["embedding"] for d in data)
        return _normalise(np.array(rows, dtype=np.float32))
