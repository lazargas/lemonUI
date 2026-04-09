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
"""
from typing import Any, Dict, List, Optional

from app.search.opensearch_client import get_opensearch_client, ACTIVITY_INDEX
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

    response = client.index(index=ACTIVITY_INDEX, body=doc, refresh=True)
    doc_id = response["_id"]
    logger.debug(f"Indexed chunk doc_id={doc_id} chunk_type={doc['chunk_type']}")
    return doc_id


def index_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Embed and store a list of chunks. Returns list of document IDs.
    """
    return [index_chunk(c) for c in chunks]


def similarity_search(
    query: str,
    k: int = 5,
    user_id: Optional[str] = None,
    sprint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Embed the query and return the top-k most similar chunks from OpenSearch.

    Optionally filter by user_id and/or sprint_id.

    Returns a list of dicts with keys: text, user_id, sprint_id, ticket_id,
    chunk_type, created_at, score.
    """
    client = get_opensearch_client()
    query_vector = embed(query)

    # Build optional filters
    filters = []
    if user_id:
        filters.append({"term": {"user_id": user_id}})
    if sprint_id:
        filters.append({"term": {"sprint_id": sprint_id}})

    knn_query: Dict[str, Any] = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": k,
                }
            }
        },
        "_source": ["text", "user_id", "sprint_id", "ticket_id", "chunk_type", "created_at"],
    }

    if filters:
        knn_query["query"] = {
            "bool": {
                "must": [knn_query["query"]],
                "filter": filters,
            }
        }

    logger.debug(
        f"OpenSearch k-NN search k={k} user_id={user_id} sprint_id={sprint_id}"
    )

    response = client.search(index=ACTIVITY_INDEX, body=knn_query)
    hits = response["hits"]["hits"]

    results = []
    for hit in hits:
        src = hit["_source"]
        src["score"] = hit["_score"]
        results.append(src)

    return results
