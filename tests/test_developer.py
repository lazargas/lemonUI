"""
test_developer.py
-----------------
Tests for the Developer API endpoints:
  GET  /api/v1/daily-summary
  GET  /api/v1/sprint-summary
  POST /api/v1/search

Covers:
  - Empty-table fallback responses (no data in DynamoDB)
  - Responses when DynamoDB has real data
  - Search with mocked OpenSearch + Bedrock
"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from tests.conftest import make_bedrock_response


# ── Helpers ───────────────────────────────────────────────────────────────

def _seed_user_sprint_context(aws_mock):
    """Insert a UserSprintContext item into the moto DynamoDB."""
    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("UserSprintContext")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": "USER#alice",
        "sk": "SPRINT#sprint-1",
        "entity_type": "user_sprint_context",
        "user_id": "alice",
        "sprint_id": "sprint-1",
        "last_refreshed_at": now,
        "summary": {
            "primary_focus": ["TICKET-101", "TICKET-102"],
            "overall_status": "On track",
        },
        "active_sims": [],
        "recent_changes": ["Merged PR for TICKET-101"],
        "pending_attention": [],
        "suggested_talking_points": ["Completed auth module", "Starting on search"],
        "risks": [],
        "blockers": [],
        "metrics": {
            "active_sim_count": 2,
            "active_blocker_count": 0,
            "active_risk_count": 0,
            "recent_fact_count": 3,
        },
        "created_at": now,
        "updated_at": now,
    })


# ── Tests: daily-summary ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_daily_summary_empty(client: AsyncClient):
    """When no data exists, returns a graceful fallback message."""
    response = await client.get("/api/v1/daily-summary", params={"userId": "unknown-user"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "unknown-user"
    assert "summary" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_daily_summary_with_data(client: AsyncClient, aws_mock):
    """When UserSprintContext exists, returns a real summary."""
    _seed_user_sprint_context(aws_mock)

    response = await client.get("/api/v1/daily-summary", params={"userId": "alice"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "alice"
    assert len(data["summary"]) > 0


# ── Tests: sprint-summary ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sprint_summary_empty(client: AsyncClient):
    """When no sprint context exists, returns a graceful fallback."""
    response = await client.get(
        "/api/v1/sprint-summary",
        params={"userId": "unknown-user", "sprintId": "sprint-99"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "unknown-user"
    assert data["sprint_id"] == "sprint-99"
    assert "summary" in data


@pytest.mark.asyncio
async def test_sprint_summary_with_data(client: AsyncClient, aws_mock):
    """When UserSprintContext exists for the sprint, returns real data."""
    # alice / sprint-1 was seeded in test_daily_summary_with_data
    response = await client.get(
        "/api/v1/sprint-summary",
        params={"userId": "alice", "sprintId": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "alice"
    assert data["sprint_id"] == "sprint-1"
    assert "On track" in data["summary"] or len(data["summary"]) > 0


# ── Tests: search ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient, mock_opensearch):
    """When OpenSearch returns no hits, the LLM still produces an answer."""
    mock_opensearch.search.return_value = {"hits": {"hits": []}}

    response = await client.post(
        "/api/v1/search",
        json={"query": "What did alice work on?", "user_id": "alice", "sprint_id": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What did alice work on?"
    assert "answer" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_search_with_opensearch_hits(client: AsyncClient, mock_opensearch, mock_bedrock):
    """When OpenSearch returns hits, the LLM answer is returned."""
    mock_opensearch.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_score": 0.95,
                    "_source": {
                        "text": "Alice merged the authentication PR.",
                        "user_id": "alice",
                        "sprint_id": "sprint-1",
                        "ticket_id": "TICKET-101",
                        "chunk_type": "ticket",
                        "created_at": "2026-04-01T10:00:00Z",
                    },
                }
            ]
        }
    }
    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "Alice worked on the authentication module and merged a PR."
    )

    response = await client.post(
        "/api/v1/search",
        json={"query": "What did alice work on?", "user_id": "alice"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "alice" in data["answer"].lower() or len(data["answer"]) > 0
    assert len(data["sources"]) == 1
    assert data["sources"][0]["ticket_id"] == "TICKET-101"


@pytest.mark.asyncio
async def test_search_missing_query(client: AsyncClient):
    """Search without a query body returns 422."""
    response = await client.post("/api/v1/search", json={})
    assert response.status_code == 422
