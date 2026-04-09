"""
conftest.py
-----------
Shared pytest fixtures for the Lemon API test suite.

Strategy
--------
- DynamoDB  → mocked with moto (no real AWS calls)
- Bedrock   → mocked with unittest.mock (returns canned text)
- OpenSearch→ mocked with unittest.mock (returns empty results)
- FastAPI   → tested via httpx AsyncClient with ASGI transport

All fixtures are session-scoped where possible so the mock DynamoDB
tables are created once and reused across tests.
"""

import json
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
from httpx import AsyncClient, ASGITransport
from moto import mock_aws

# ── Point boto3 at the moto fake endpoint before any app code imports ──────
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
# Prevent the app from trying to connect to a real OpenSearch endpoint
os.environ.setdefault("OPENSEARCH_ENDPOINT", "https://mock.opensearch.local")
os.environ.setdefault("OPENSEARCH_INDEX", "activity-embeddings")


# ── DynamoDB table definitions (mirrors dynamo-stack.ts) ──────────────────

TABLE_DEFS = [
    {
        "TableName": "ProjectFacts",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "gsi1pk", "AttributeType": "S"},
            {"AttributeName": "gsi1sk", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "gsi1pk-gsi1sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "ProjectSprintContext",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "gsi1pk", "AttributeType": "S"},
            {"AttributeName": "gsi1sk", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "gsi1pk-gsi1sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "Projects",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "SimEvents",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "gsi1pk", "AttributeType": "S"},
            {"AttributeName": "gsi1sk", "AttributeType": "S"},
            {"AttributeName": "gsi2pk", "AttributeType": "S"},
            {"AttributeName": "gsi2sk", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "gsi1pk-gsi1sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi2pk-gsi2sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi2pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi2sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "UserSprintContext",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "UserSprintFacts",
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "gsi1pk", "AttributeType": "S"},
            {"AttributeName": "gsi1sk", "AttributeType": "S"},
            {"AttributeName": "gsi2pk", "AttributeType": "S"},
            {"AttributeName": "gsi2sk", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "gsi1pk-gsi1sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi2pk-gsi2sk-index",
                "KeySchema": [
                    {"AttributeName": "gsi2pk", "KeyType": "HASH"},
                    {"AttributeName": "gsi2sk", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def _create_tables(ddb_client):
    """Create all DynamoDB tables in the moto mock."""
    for defn in TABLE_DEFS:
        ddb_client.create_table(**defn)


# ── Mock helpers ──────────────────────────────────────────────────────────

def make_bedrock_response(text: str) -> dict:
    """Build a fake Bedrock invoke_model response."""
    body_bytes = json.dumps({"content": [{"text": text}]}).encode()
    mock_stream = MagicMock()
    mock_stream.read.return_value = body_bytes
    return {"body": mock_stream}


def make_opensearch_empty_response() -> dict:
    """Build a fake empty OpenSearch search response."""
    return {"hits": {"hits": []}}


# ── Session-scoped mock AWS + app client ──────────────────────────────────

@pytest.fixture(scope="session")
def aws_mock():
    """Start moto mock for the entire test session."""
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _create_tables(ddb)
        yield ddb


@pytest.fixture(scope="session")
def mock_bedrock(aws_mock):
    """Mock Bedrock runtime so no real LLM calls are made."""
    with patch("app.llm.bedrock_client.get_bedrock_runtime") as mock_fn:
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = make_bedrock_response(
            "This is a mocked LLM response for testing."
        )
        mock_fn.return_value = mock_client
        yield mock_client


@pytest.fixture(scope="session")
def mock_opensearch(aws_mock):
    """Mock OpenSearch client so no real vector search calls are made."""
    with patch("app.search.opensearch_client.get_opensearch_client") as mock_fn:
        mock_client = MagicMock()
        mock_client.indices.exists.return_value = True
        mock_client.search.return_value = make_opensearch_empty_response()
        mock_client.index.return_value = {"_id": "mock-doc-id"}
        mock_fn.return_value = mock_client
        # Also mock the embed() function so Bedrock is never called for embeddings
        with patch("app.search.embeddings.embed", return_value=[0.0] * 1536):
            yield mock_client


@pytest_asyncio.fixture(scope="session")
async def client(aws_mock, mock_bedrock, mock_opensearch):
    """
    FastAPI test client with all AWS services mocked.
    The lru_cache on get_dynamodb_resource must be cleared so moto's
    fake endpoint is used instead of a cached real one.
    """
    from app.db.dynamo import get_dynamodb_resource, get_dynamodb_client
    get_dynamodb_resource.cache_clear()
    get_dynamodb_client.cache_clear()

    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
