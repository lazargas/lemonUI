import boto3
from functools import lru_cache
from app.core.config import settings


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    """Return a cached DynamoDB resource."""
    kwargs = dict(region_name=settings.AWS_REGION)
    if settings.AWS_ENDPOINT_URL:          # useful for local DynamoDB
        kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
    return boto3.resource("dynamodb", **kwargs)


@lru_cache(maxsize=1)
def get_dynamodb_client():
    """Return a cached DynamoDB low-level client."""
    kwargs = dict(region_name=settings.AWS_REGION)
    if settings.AWS_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
    return boto3.client("dynamodb", **kwargs)


def get_table(table_name: str):
    """Helper to get a DynamoDB Table resource by name."""
    return get_dynamodb_resource().Table(table_name)
