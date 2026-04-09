"""
test_jobs.py
------------
Tests for the Jobs API endpoints (manual summary job triggers):
  POST /api/v1/jobs/daily-summary
  POST /api/v1/jobs/sprint-summary
  POST /api/v1/jobs/roadmap-summary

Bedrock is mocked so no real LLM calls are made.
DynamoDB is mocked via moto.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import make_bedrock_response


# ── Tests: POST /jobs/daily-summary ──────────────────────────────────────

@pytest.mark.asyncio
async def test_daily_summary_job_no_data(client: AsyncClient, mock_bedrock):
    """
    When no DynamoDB data exists, the job still runs and calls the LLM
    with a placeholder activity text.
    """
    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "Yesterday I worked on setting up the project scaffolding."
    )
    response = await client.post(
        "/api/v1/jobs/daily-summary", params={"userId": "bob"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "daily_summary"
    assert data["user_id"] == "bob"
    assert data["status"] in ("completed", "failed")
    assert "started_at" in data
    assert "completed_at" in data


@pytest.mark.asyncio
async def test_daily_summary_job_with_data(client: AsyncClient, aws_mock, mock_bedrock):
    """
    When UserSprintContext exists, the job fetches it and calls the LLM.
    """
    # Seed a context for bob
    import boto3
    from datetime import datetime, timezone
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("UserSprintContext")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": "USER#bob",
        "sk": "SPRINT#sprint-2",
        "entity_type": "user_sprint_context",
        "user_id": "bob",
        "sprint_id": "sprint-2",
        "last_refreshed_at": now,
        "summary": {"primary_focus": ["TICKET-200"], "overall_status": "On track"},
        "active_sims": [],
        "recent_changes": [],
        "pending_attention": [],
        "suggested_talking_points": [],
        "risks": [],
        "blockers": [],
        "metrics": {
            "active_sim_count": 1,
            "active_blocker_count": 0,
            "active_risk_count": 0,
            "recent_fact_count": 0,
        },
        "created_at": now,
        "updated_at": now,
    })

    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "Yesterday Bob worked on TICKET-200 and made good progress."
    )

    response = await client.post(
        "/api/v1/jobs/daily-summary", params={"userId": "bob"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["user_id"] == "bob"
    assert data["sprint_id"] == "sprint-2"
    assert data["summary_preview"] is not None


# ── Tests: POST /jobs/sprint-summary ─────────────────────────────────────

@pytest.mark.asyncio
async def test_sprint_summary_job_no_data(client: AsyncClient, mock_bedrock):
    """Sprint summary job runs even when no facts exist in DynamoDB."""
    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "This sprint the developer focused on infrastructure work."
    )
    response = await client.post(
        "/api/v1/jobs/sprint-summary",
        params={"userId": "charlie", "sprintId": "sprint-99"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "sprint_summary"
    assert data["user_id"] == "charlie"
    assert data["sprint_id"] == "sprint-99"
    assert data["status"] in ("completed", "failed")


@pytest.mark.asyncio
async def test_sprint_summary_job_missing_params(client: AsyncClient):
    """Missing required query params returns 422."""
    response = await client.post("/api/v1/jobs/sprint-summary", params={"userId": "alice"})
    assert response.status_code == 422


# ── Tests: POST /jobs/roadmap-summary ────────────────────────────────────

@pytest.mark.asyncio
async def test_roadmap_summary_job_no_data(client: AsyncClient, mock_bedrock):
    """Roadmap summary job runs even when no project facts exist."""
    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "Overall the sprint is progressing well with no major blockers."
    )
    response = await client.post(
        "/api/v1/jobs/roadmap-summary", params={"sprintId": "sprint-99"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "roadmap_summary"
    assert data["sprint_id"] == "sprint-99"
    assert data["status"] in ("completed", "failed")
    assert "started_at" in data
    assert "completed_at" in data


@pytest.mark.asyncio
async def test_roadmap_summary_job_with_facts(client: AsyncClient, aws_mock, mock_bedrock):
    """Roadmap summary job fetches project facts and calls LLM."""
    import boto3
    from datetime import datetime, timezone
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("ProjectFacts")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": "PROJECT#proj-2",
        "sk": f"FACT#{now}#fact-002",
        "gsi1pk": "SPRINT#sprint-3",
        "gsi1sk": "PROJECT#proj-2",
        "entity_type": "project_fact",
        "fact_id": "fact-002",
        "project_id": "proj-2",
        "project_name": "Search Service",
        "sprint_id": "sprint-3",
        "fact_type": "risk",
        "fact_time": now,
        "summary": "OpenSearch cluster is at 80% capacity.",
        "details": {},
        "source_sim_ids": [],
        "source_user_ids": [],
        "evidence_event_ids": [],
        "confidence_score": "0.85",
        "importance_score": "0.9",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    mock_bedrock.invoke_model.return_value = make_bedrock_response(
        "Sprint 3 has a capacity risk in the Search Service that needs attention."
    )

    response = await client.post(
        "/api/v1/jobs/roadmap-summary", params={"sprintId": "sprint-3"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["sprint_id"] == "sprint-3"
    assert data["summary_preview"] is not None


@pytest.mark.asyncio
async def test_roadmap_summary_job_missing_sprint(client: AsyncClient):
    """Missing sprintId returns 422."""
    response = await client.post("/api/v1/jobs/roadmap-summary")
    assert response.status_code == 422
