import hashlib
import math
from typing import Sequence

import litellm

from coding_assistant.config import get_settings


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    settings = get_settings()
    if settings.embedding_model and texts:
        try:
            response = await litellm.aembedding(model=settings.embedding_model, input=list(texts))
            return [item["embedding"] for item in response.data]
        except Exception:
            pass
    dim = get_settings().embedding_dimensions
    return [_deterministic_embedding(t, dim) for t in texts]


def _deterministic_embedding(text: str, dim: int) -> list[float]:
    """Offline-safe fallback when no embedding API is configured."""
    vec = [0.0] * dim
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        for i in range(dim):
            vec[i] += (digest[i % len(digest)] - 128) / 128.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
