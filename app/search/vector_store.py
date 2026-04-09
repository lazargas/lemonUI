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
        index=get_activity_index(), body=doc, params={"refresh": "true"}
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

    logger.debug(
        f"OpenSearch k-NN search k={k} user_id={user_id} sprint_id={sprint_id}"
    )

    response = client.search(index=get_activity_index(), body=search_body)
    hits = response["hits"]["hits"]

    results = []
    for hit in hits:
        src = hit["_source"]
        src["score"] = hit["_score"]
        results.append(src)

    return results
