"""
Bedrock Client
--------------
Cached boto3 Bedrock runtime client.
Uses the IAM role attached to the EC2 instance — no hardcoded credentials.
"""
import boto3
from functools import lru_cache
from app.core.config import settings


@lru_cache(maxsize=1)
def get_bedrock_runtime():
    """Return a cached Bedrock runtime client."""
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
    )
