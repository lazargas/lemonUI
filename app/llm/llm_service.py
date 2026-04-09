"""
LLM Service
-----------
Calls Claude 3 Sonnet on Amazon Bedrock.
Provides a single `generate()` function used by all summary and search flows.
"""
import json
from typing import List

from app.llm.bedrock_client import get_bedrock_runtime
from app.core.config import settings
from app.utils.logger import logger


def generate(prompt: str, max_tokens: int = 1024) -> str:
    """
    Send a prompt to Claude 3 Sonnet on Bedrock and return the response text.

    Args:
        prompt:     The fully-rendered prompt string (use prompts.py templates).
        max_tokens: Maximum tokens in the response (default 1024).

    Returns:
        The model's text response as a plain string.
    """
    client = get_bedrock_runtime()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    logger.info(
        f"Calling Bedrock model={settings.BEDROCK_MODEL_ID} "
        f"max_tokens={max_tokens}"
    )

    try:
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        logger.info("Bedrock response received successfully")
        return text.strip()

    except Exception as e:
        logger.error(f"Bedrock invocation failed: {e}")
        raise
