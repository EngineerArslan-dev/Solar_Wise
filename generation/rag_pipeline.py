"""
rag_pipeline.py
----------------
Ties retrieval (vectorstore) + deterministic calculation (validation) +
generation (Claude) together.

Design principle: the LLM is NOT trusted to do arithmetic or invent
standards citations. It only:
  1. Synthesizes an explanation grounded in retrieved document chunks
     (with citations back to doc_id/title).
  2. Narrates results of formula_validator.py calculations that WE
     computed in Python and pass in as already-correct numbers.

This keeps the "engineering credibility" claim honest: numbers come from
tested functions, standards come from retrieved source text, and the LLM's
job is synthesis and clear communication — not invention.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, TOP_K_RETRIEVAL
from vectorstore.vector_db import SolarKnowledgeBase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a PhD-level electrical engineer specializing in \
photovoltaic system design, serving as the reasoning layer of a \
retrieval-augmented generation (RAG) system for solar sizing in Pakistan.

Hard rules:
1. Ground every technical claim in the provided CONTEXT chunks. If the \
context does not support a claim, say so explicitly rather than inventing \
a citation or a standard's contents.
2. Never perform sizing arithmetic yourself. If numeric results are \
supplied under CALCULATED RESULTS, narrate and explain them — do not \
recompute or alter the figures.
3. When citing a source, reference it by its title/doc_id as given in the \
context, e.g., "(Source: NEPRA Net Metering Regulations)".
4. Flag any validation warnings supplied to you prominently — do not bury \
or omit them.
5. If retrieved context is thin or absent for part of the question, say \
so plainly instead of filling the gap from general training knowledge \
presented as if it were sourced.
"""


@dataclass
class RAGResponse:
    answer: str
    retrieved_chunks: List[Dict]
    calculated_results: Optional[Dict] = None


def _format_context(chunks: List[Dict]) -> str:
    if not chunks:
        return "(No relevant documents retrieved from the knowledge base.)"
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(
            f"[{i}] Source: {c.get('title', 'Unknown')} "
            f"(category: {c.get('category', 'unknown')}, doc_id: {c.get('doc_id', 'n/a')})\n"
            f"{c['text']}"
        )
    return "\n\n".join(blocks)


def _format_calculations(calculated_results: Optional[Dict]) -> str:
    if not calculated_results:
        return "(No calculation was requested for this query.)"
    lines = []
    for name, result in calculated_results.items():
        lines.append(f"- {name}: {result.value} {result.unit}")
        lines.append(f"  formula: {result.formula}")
        if result.assumptions:
            lines.append(f"  assumptions: {result.assumptions}")
        for w in result.warnings:
            lines.append(f"  ⚠ WARNING: {w}")
    return "\n".join(lines)


def answer_query(
    query: str,
    kb: SolarKnowledgeBase,
    top_k: int = TOP_K_RETRIEVAL,
    category_filter: Optional[str] = None,
    calculated_results: Optional[Dict] = None,
) -> RAGResponse:
    """
    Run one RAG turn: retrieve relevant chunks, optionally attach
    pre-computed calculation results, and generate a grounded answer.

    `calculated_results` should be a dict of name -> CalculationResult
    (see validation/formula_validator.py), e.g.:
        {"Array size": size_array(...), "Battery bank": size_battery_bank(...)}
    """
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise ImportError("anthropic SDK required. Install with: pip install anthropic") from e

    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Set it before calling answer_query()."
        )

    retrieved = kb.query(query, top_k=top_k, category_filter=category_filter)
    context_block = _format_context(retrieved)
    calc_block = _format_calculations(calculated_results)

    user_message = f"""QUESTION:
{query}

CONTEXT (retrieved from knowledge base):
{context_block}

CALCULATED RESULTS (already computed by validated Python functions — do not recompute):
{calc_block}

Provide a clear, well-organized answer. Cite sources by title where you use them. \
If context is insufficient for any part of the answer, state that explicitly."""

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    answer_text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )

    return RAGResponse(
        answer=answer_text,
        retrieved_chunks=retrieved,
        calculated_results=calculated_results,
    )
