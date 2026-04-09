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

# k-NN index name used for all activity embeddings
ACTIVITY_INDEX = "lemon-activity"

# Embedding dimensions (must match Titan Embeddings V2 output)
EMBEDDING_DIMS = 1536


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
    Safe to call on every startup.
    """
    client = get_opensearch_client()

    if client.indices.exists(index=ACTIVITY_INDEX):
        logger.info(f"OpenSearch index '{ACTIVITY_INDEX}' already exists")
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
                        "engine": "nmslib",
                    },
                },
                "text": {"type": "text"},
                "user_id": {"type": "keyword"},
                "sprint_id": {"type": "keyword"},
                "ticket_id": {"type": "keyword"},
                "chunk_type": {"type": "keyword"},  # "ticket" | "comment" | "summary"
                "created_at": {"type": "date"},
            }
        },
    }

    client.indices.create(index=ACTIVITY_INDEX, body=index_body)
    logger.info(f"Created OpenSearch k-NN index '{ACTIVITY_INDEX}'")
