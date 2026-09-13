"""
groq_pipeline.py
-----------------
RAG generation adapter for Groq, matching the Solar Wise PRD's specified
AI/LLM stack (Section 7.1: "AI / LLM: Groq API").

This mirrors generation/rag_pipeline.py's Anthropic-based implementation
exactly in structure and guardrails — same retrieval call, same system
prompt discipline, same refusal to compute or invent figures — swapped
onto Groq's OpenAI-compatible chat completions endpoint. Hassan's
Streamlit/AI integration layer should call answer_query() from whichever
of the two adapters the team standardizes on; both return the same
RAGResponse shape.

PRD guardrails enforced here (Section 6.2):
  - The LLM never generates or alters a numeric result — numbers must be
    passed in via `calculated_results`, computed upstream by Qadeer's
    Python engine, never computed by this module or the model itself.
  - The LLM never states a spec/price/regulation absent from retrieved
    context — the system prompt instructs it to say so explicitly
    instead of guessing.

Model note: Groq deprecates and replaces models on a running basis
(e.g., llama-3.3-70b-versatile was deprecated August 2026 in favor of
openai/gpt-oss-120b). GROQ_MODEL is read from the environment so this
doesn't need a code change when Groq's lineup shifts — check
https://console.groq.com/docs/models for the current list before a demo.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from config import TOP_K_RETRIEVAL
from vectorstore.vector_db import SolarKnowledgeBase
from generation.rag_pipeline import (
    RAGResponse, SYSTEM_PROMPT, _format_context, _format_calculations
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def answer_query_groq(
    query: str,
    kb: SolarKnowledgeBase,
    top_k: int = TOP_K_RETRIEVAL,
    category_filter: Optional[str] = None,
    calculated_results: Optional[Dict] = None,
) -> RAGResponse:
    """
    Groq equivalent of generation/rag_pipeline.answer_query(). Same
    signature, same RAGResponse return shape, same guardrail system
    prompt — only the model backend differs.
    """
    try:
        from groq import Groq
    except ImportError as e:
        raise ImportError("groq SDK required. Install with: pip install groq") from e

    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable not set. "
            "Set it before calling answer_query_groq()."
        )

    retrieved = kb.query(query, top_k=top_k, category_filter=category_filter)
    context_block = _format_context(retrieved)
    calc_block = _format_calculations(calculated_results)

    user_message = f"""QUESTION:
{query}

CONTEXT (retrieved from knowledge base):
{context_block}

CALCULATED RESULTS (already computed by the Python engine — do not recompute):
{calc_block}

Provide a clear, well-organized answer. Cite sources by title where you use them. \
If context is insufficient for any part of the answer, state that explicitly."""

    client = Groq(api_key=GROQ_API_KEY)
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    answer_text = completion.choices[0].message.content

    return RAGResponse(
        answer=answer_text,
        retrieved_chunks=retrieved,
        calculated_results=calculated_results,
    )
