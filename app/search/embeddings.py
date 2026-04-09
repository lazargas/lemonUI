"""
Embeddings
----------
Generates text embeddings using Amazon Bedrock Titan Embeddings V2.
Returns a 1536-dimensional float vector for any input text.
"""
import json
from typing import List

from app.llm.bedrock_client import get_bedrock_runtime
from app.core.config import settings
from app.utils.logger import logger


def embed(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text using Titan Embeddings V2.

    Args:
        text: The input text to embed (ticket, comment, summary chunk, or query).

    Returns:
        A list of 1536 floats representing the semantic embedding.
    """
    client = get_bedrock_runtime()

    body = {
        "inputText": text,
        "dimensions": 1536,
        "normalize": True,
    }

    logger.debug(
        f"Generating embedding model={settings.BEDROCK_EMBEDDING_MODEL_ID} "
        f"text_length={len(text)}"
    )

    try:
        response = client.invoke_model(
            modelId=settings.BEDROCK_EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Titan Embeddings does not support batch natively — calls embed() per item.
    """
    return [embed(t) for t in texts]
