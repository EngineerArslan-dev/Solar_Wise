"""
vector_db.py
------------
Thin wrapper around a persistent ChromaDB collection. Handles:
  - adding chunks (with embeddings + metadata) to the store
  - similarity search with optional metadata filtering (e.g., restrict
    a query to category="pk_regulation_tariff" only)
  - basic collection stats

ChromaDB was chosen over FAISS here because it stores metadata and text
alongside vectors natively (FAISS is index-only), which matters for a
system that needs to cite *which standard/document* backed an answer.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from config import CHROMA_DB_DIR, COLLECTION_NAME
from processing.chunker import Chunk
from processing.embeddings import embed_texts, embed_query

logger = logging.getLogger(__name__)


class SolarKnowledgeBase:
    def __init__(self, persist_dir=CHROMA_DB_DIR, collection_name: str = COLLECTION_NAME):
        try:
            import chromadb
        except ImportError as e:
            raise ImportError("chromadb is required. Install with: pip install chromadb") from e

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[Chunk], batch_size: int = 64) -> int:
        """Embed and upsert chunks into the collection. Returns count added."""
        if not chunks:
            return 0

        added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.text for c in batch]
            vectors = embed_texts(texts)
            ids = [c.chunk_id for c in batch]
            metadatas = [
                {
                    "doc_id": c.doc_id,
                    "category": c.category,
                    "title": c.title,
                    **{k: v for k, v in c.metadata.items() if isinstance(v, (str, int, float, bool))},
                }
                for c in batch
            ]
            self._collection.upsert(
                ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas
            )
            added += len(batch)
            logger.info("Upserted batch %d-%d / %d chunks", i, i + len(batch), len(chunks))

        return added

    def query(
        self,
        query_text: str,
        top_k: int = 6,
        category_filter: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return the top_k most similar chunks to query_text.

        Each result dict has: text, doc_id, title, category, distance.
        Lower distance = more similar (cosine distance).
        """
        query_vector = embed_query(query_text)

        where = {"category": category_filter} if category_filter else None

        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
        )

        output = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for text, meta, dist in zip(docs, metas, dists):
            output.append({
                "text": text,
                "doc_id": meta.get("doc_id"),
                "title": meta.get("title"),
                "category": meta.get("category"),
                "distance": dist,
            })
        return output

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Delete all vectors in the collection (irreversible)."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name, metadata={"hnsw:space": "cosine"}
        )
