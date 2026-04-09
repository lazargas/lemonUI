"""
Search Service
--------------
Full search pipeline:
  1. Receive natural-language query
  2. Embed query using Titan Embeddings V2
  3. Retrieve top-k relevant chunks from OpenSearch Serverless
  4. Send chunks + query to Claude 3 Sonnet on Bedrock
  5. Return the LLM answer with source references
"""
from typing import Any, Dict, List, Optional

from app.search.vector_store import similarity_search
from app.llm.llm_service import generate
from app.llm.prompts import SEARCH_ANSWER_PROMPT
from app.utils.logger import logger


def search(
    query: str,
    user_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
    k: int = 5,
) -> Dict[str, Any]:
    """
    Answer a natural-language question about developer activity.

    Args:
        query:     The user's free-text question.
        user_id:   Optional filter — restrict search to one developer.
        sprint_id: Optional filter — restrict search to one sprint.
        k:         Number of context chunks to retrieve (default 5).

    Returns:
        {
            "query":   str,
            "answer":  str,
            "sources": [ { text, user_id, sprint_id, ticket_id, chunk_type, score } ]
        }
    """
    logger.info(
        f"Search pipeline query='{query}' user_id={user_id} sprint_id={sprint_id} k={k}"
    )

    # ── Step 1: Semantic retrieval ─────────────────────────────────────────
    chunks = similarity_search(
        query=query,
        k=k,
        user_id=user_id,
        sprint_id=sprint_id,
    )

    if not chunks:
        logger.warning("No relevant chunks found in OpenSearch for query")
        return {
            "query": query,
            "answer": (
                "No relevant activity data was found for this query. "
                "The index may be empty or the query may not match any stored activity."
            ),
            "sources": [],
        }

    # ── Step 2: Build context string ───────────────────────────────────────
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = f"[{i}] ({chunk.get('chunk_type', 'unknown')} | {chunk.get('ticket_id', 'N/A')} | {chunk.get('created_at', 'N/A')})"
        context_parts.append(f"{meta}\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    # ── Step 3: LLM answer ─────────────────────────────────────────────────
    prompt = SEARCH_ANSWER_PROMPT.format(query=query, context=context)
    answer = generate(prompt, max_tokens=512)

    logger.info(f"Search answer generated for query='{query}'")

    return {
        "query": query,
        "answer": answer,
        "sources": chunks,
    }
