"""
chunker.py
----------
Splits long documents into overlapping chunks sized for embedding.

Deliberately dependency-free (no langchain) — a simple recursive
character splitter that prefers to break on paragraph/sentence
boundaries before falling back to a hard character cut. This keeps
technical clauses (e.g., a full formula or a standard's clause) from
being severed mid-sentence where avoidable.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import List

from config import CHUNK_SIZE, CHUNK_OVERLAP
from data_ingestion.document_loader import RawDocument

# Preference order for split points, largest structural unit first
_SPLIT_PATTERNS = [
    r"\n\s*\n",       # paragraph breaks
    r"(?<=[.!?])\s+", # sentence boundaries
    r",\s+",          # clause boundaries
    r"\s+",           # last resort: any whitespace
]


@dataclass
class Chunk:
    chunk_id: str
    text: str
    doc_id: str
    category: str
    title: str
    metadata: dict = field(default_factory=dict)


def _split_on_pattern(text: str, pattern: str) -> List[str]:
    parts = re.split(pattern, text)
    return [p for p in parts if p and p.strip()]


def _recursive_split(text: str, max_size: int, pattern_idx: int = 0) -> List[str]:
    """Try splitting by the current pattern; recurse into pieces still
    too large, escalating to a finer-grained pattern each time."""
    if len(text) <= max_size:
        return [text]

    if pattern_idx >= len(_SPLIT_PATTERNS):
        # Hard cut as an absolute last resort
        return [text[i:i + max_size] for i in range(0, len(text), max_size)]

    pieces = _split_on_pattern(text, _SPLIT_PATTERNS[pattern_idx])
    if len(pieces) <= 1:
        return _recursive_split(text, max_size, pattern_idx + 1)

    result: List[str] = []
    for piece in pieces:
        if len(piece) > max_size:
            result.extend(_recursive_split(piece, max_size, pattern_idx + 1))
        else:
            result.append(piece)
    return result


def _merge_with_overlap(pieces: List[str], max_size: int, overlap: int) -> List[str]:
    """Greedily pack small pieces up to max_size, then start the next
    chunk with a trailing `overlap` characters of the previous chunk so
    context isn't lost at boundaries."""
    chunks: List[str] = []
    current = ""

    for piece in pieces:
        candidate = (current + " " + piece).strip() if current else piece
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # seed next chunk with overlap tail from the chunk just closed
            tail = current[-overlap:] if current and overlap > 0 else ""
            current = (tail + " " + piece).strip() if tail else piece
            # if a single piece alone still exceeds max_size, hard-split it
            while len(current) > max_size:
                chunks.append(current[:max_size])
                current = current[max_size - overlap:]

    if current:
        chunks.append(current)

    return chunks


def chunk_document(doc: RawDocument, chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> List[Chunk]:
    """Split one RawDocument into a list of Chunk objects."""
    pieces = _recursive_split(doc.text, chunk_size)
    merged = _merge_with_overlap(pieces, chunk_size, overlap)

    chunks = []
    for i, text in enumerate(merged):
        chunks.append(Chunk(
            chunk_id=f"{doc.doc_id}::chunk{i}::{uuid.uuid4().hex[:8]}",
            text=text.strip(),
            doc_id=doc.doc_id,
            category=doc.category,
            title=doc.title,
            metadata={**doc.metadata, "chunk_index": i, "source_path": doc.source_path},
        ))
    return chunks


def chunk_documents(docs: List[RawDocument], chunk_size: int = CHUNK_SIZE,
                     overlap: int = CHUNK_OVERLAP) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size, overlap))
    return all_chunks
