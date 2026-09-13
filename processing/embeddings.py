"""
embeddings.py
-------------
Generates vector embeddings locally using sentence-transformers, so the
system doesn't need to send document text to a third-party embedding API
(useful given that some ingested documents — e.g., NEPRA tariff PDFs —
may be sensitive/internal, or you simply want zero per-call embedding
cost).

Model: all-MiniLM-L6-v2 (384-dim, fast, strong general retrieval quality
for its size — a standard default for local RAG pipelines).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from config import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    """Lazily load the embedding model once per process."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            "sentence-transformers is required. Install with: "
            "pip install sentence-transformers"
        ) from e

    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Embed a list of strings, returning a list of float vectors."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 50,
        normalize_embeddings=True,  # cosine similarity becomes a dot product
    )
    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]
