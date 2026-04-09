"""
OpenSearch Serverless Client
-----------------------------
SigV4-authenticated client for Amazon OpenSearch Serverless.
Uses the IAM role attached to the EC2 instance — no hardcoded credentials.
"""
from functools import lru_cache

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

from app.core.config import settings
from app.utils.logger import logger

# Embedding dimensions (must match Titan Embeddings V2 output)
EMBEDDING_DIMS = 1536


def get_activity_index() -> str:
    """Return the configured OpenSearch index name."""
    return settings.OPENSEARCH_INDEX


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    """Return a cached, SigV4-authenticated OpenSearch Serverless client."""
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, settings.AWS_REGION, "aoss")

    host = settings.OPENSEARCH_ENDPOINT.replace("https://", "").rstrip("/")

    logger.info(f"Connecting to OpenSearch Serverless host={host}")

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )


def ensure_index_exists() -> None:
    """
    Create the k-NN index if it does not already exist.
    Safe to call on every startup — non-fatal if OpenSearch is unreachable.

    Notes:
    - OpenSearch Serverless only supports the 'faiss' k-NN engine (not nmslib).
    - Uses the index name from settings so it stays in sync with the rest of the app.
    """
    index_name = get_activity_index()

    try:
        client = get_opensearch_client()

        if client.indices.exists(index=index_name):
            logger.info(f"OpenSearch index '{index_name}' already exists")
            return

        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            # OpenSearch Serverless only supports 'faiss' (not 'nmslib')
                            "engine": "faiss",
                        },
                    },
                    "text": {"type": "text"},
                    "user_id": {"type": "keyword"},
                    "sprint_id": {"type": "keyword"},
                    "ticket_id": {"type": "keyword"},
                    "chunk_type": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            },
        }

        client.indices.create(index=index_name, body=index_body)
        logger.info(f"Created OpenSearch k-NN index '{index_name}'")

    except Exception as exc:
        # Non-fatal: app can still serve DynamoDB-backed endpoints without OpenSearch
        logger.warning(
            f"Could not ensure OpenSearch index exists (non-fatal): {exc}"
        )
