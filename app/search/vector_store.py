"""
Vector Store
------------
Wraps OpenSearch Serverless for storing and searching activity embeddings.

Chunk schema:
    {
        "text":       str,          # raw text of the chunk
        "user_id":    str,
        "sprint_id":  str,
        "ticket_id":  str | None,
        "chunk_type": str,          # "ticket" | "comment" | "summary"
        "created_at": str,          # ISO-8601
    }

OpenSearch Serverless k-NN query notes
---------------------------------------
- Use top-level "knn" query (not nested inside "bool.must") for pure vector search.
- For filtered vector search, use "knn" query with a "filter" clause at the same
  level as "vector" and "k" (supported in OpenSearch 2.9+ / Serverless).
- Do NOT wrap the knn query inside a bool.must — that disables the HNSW index.
"""
from typing import Any, Dict, List, Optional

from app.search.opensearch_client import get_opensearch_client, get_activity_index
from app.search.embeddings import embed
from app.utils.logger import logger


def index_chunk(chunk: Dict[str, Any]) -> str:
    """
    Embed a single chunk and store it in OpenSearch.
    Returns the OpenSearch document ID.
    """
    client = get_opensearch_client()
    vector = embed(chunk["text"])

    doc = {
        "embedding": vector,
        "text": chunk["text"],
        "user_id": chunk.get("user_id", ""),
        "sprint_id": chunk.get("sprint_id", ""),
        "ticket_id": chunk.get("ticket_id", ""),
        "chunk_type": chunk.get("chunk_type", "ticket"),
        "created_at": chunk.get("created_at", ""),
    }

    response = client.index(
        index=get_activity_index(), body=doc
    )
    doc_id = response["_id"]
    logger.debug(f"Indexed chunk doc_id={doc_id} chunk_type={doc['chunk_type']}")
    return doc_id


def index_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """Embed and store a list of chunks. Returns list of document IDs."""
    return [index_chunk(c) for c in chunks]


def similarity_search(
    query: str,
    k: int = 5,
    user_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Embed the query and return the top-k most similar chunks from OpenSearch.

    Uses the k-NN "filter" approach supported by OpenSearch Serverless:
    the filter is placed inside the knn field query (not in a bool wrapper)
    so the HNSW index is still used for ANN retrieval.

    Returns a list of dicts with keys:
        text, user_id, sprint_id, ticket_id, chunk_type, created_at, score
    """
    client = get_opensearch_client()
    query_vector = embed(query)

    # Build optional pre-filters (applied inside the k-NN engine)
    knn_filters: List[Dict[str, Any]] = []
    if user_id:
        knn_filters.append({"term": {"user_id": user_id}})
    if sprint_id:
        knn_filters.append({"term": {"sprint_id": sprint_id}})

    # k-NN field query — filter lives inside the knn clause for Serverless
    knn_field: Dict[str, Any] = {
        "vector": query_vector,
        "k": k,
    }
    if knn_filters:
        knn_field["filter"] = (
            {"bool": {"must": knn_filters}} if len(knn_filters) > 1
            else knn_filters[0]
        )

    search_body: Dict[str, Any] = {
        "size": k,
        "query": {
            "knn": {
                "embedding": knn_field,
            }
        },
        "_source": [
            "text", "user_id", "sprint_id", "ticket_id", "chunk_type", "created_at"
        ],
    }

    index_name = get_activity_index()
    logger.info(
        f"[OPENSEARCH SEARCH] → index={index_name} k={k} "
        f"user_id={user_id} sprint_id={sprint_id} "
        f"has_filter={bool(knn_filters)}"
    )
    logger.info(f"[OPENSEARCH SEARCH] → query_body={search_body}")

    try:
        response = client.search(index=index_name, body=search_body)
    except Exception as e:
        logger.error(f"[OPENSEARCH SEARCH] ✗ Search failed: {type(e).__name__}: {e}")
        raise

    hits = response["hits"]["hits"]
    total = response["hits"].get("total", {})
    logger.info(
        f"[OPENSEARCH SEARCH] ← index={index_name} "
        f"total_hits={total} returned={len(hits)}"
    )
    for i, hit in enumerate(hits):
        logger.info(
            f"[OPENSEARCH SEARCH] ← hit[{i}] score={hit['_score']} "
            f"chunk_type={hit['_source'].get('chunk_type')} "
            f"user_id={hit['_source'].get('user_id')} "
            f"text_preview={hit['_source'].get('text','')[:100]!r}"
        )

    results = []
    for hit in hits:
        src = hit["_source"]
        src["score"] = hit["_score"]
        results.append(src)

    return results
