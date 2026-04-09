"""
test_project.py
---------------
Tests for the Project API endpoints:
  GET /api/v1/projects
  GET /api/v1/projects/{projectId}/sprint-context
  GET /api/v1/projects/{projectId}/facts
  GET /api/v1/projects/{projectId}/timeline
  GET /api/v1/leadership/roadmap-summary
"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient


# ── Seed helpers ──────────────────────────────────────────────────────────

def _seed_project_sprint_context(aws_mock, project_id: str = "proj-1", sprint_id: str = "sprint-1"):
    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("ProjectSprintContext")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": f"PROJECT#{project_id}",
        "sk": f"SPRINT#{sprint_id}",
        "gsi1pk": f"SPRINT#{sprint_id}",
        "gsi1sk": f"PROJECT#{project_id}",
        "entity_type": "project_sprint_context",
        "project_id": project_id,
        "project_name": "Auth Service",
        "sprint_id": sprint_id,
        "last_refreshed_at": now,
        "summary": {
            "overall_status": "In progress",
            "health": "GREEN",
            "completion_confidence": "HIGH",
        },
        "active_users": [],
        "active_sims": [],
        "recent_changes": ["Added OAuth2 support"],
        "risks": [{"summary": "Third-party API rate limit", "severity": "MEDIUM"}],
        "blockers": [],
        "dependencies": [{"summary": "Depends on identity service"}],
        "leadership_summary": {
            "one_liner": "Auth service is on track for sprint completion.",
            "what_changed": [],
            "needs_attention": [],
        },
        "metrics": {
            "active_sim_count": 3,
            "active_user_count": 2,
            "active_risk_count": 1,
            "active_blocker_count": 0,
        },
        "created_at": now,
        "updated_at": now,
    })


def _seed_project_fact(aws_mock, project_id: str = "proj-1", sprint_id: str = "sprint-1"):
    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("ProjectFacts")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": f"PROJECT#{project_id}",
        "sk": f"FACT#{now}#fact-001",
        "gsi1pk": f"SPRINT#{sprint_id}",
        "gsi1sk": f"PROJECT#{project_id}",
        "entity_type": "project_fact",
        "fact_id": "fact-001",
        "project_id": project_id,
        "project_name": "Auth Service",
        "sprint_id": sprint_id,
        "fact_type": "blocker",
        "fact_time": now,
        "summary": "OAuth provider is returning 429 errors intermittently.",
        "details": {},
        "source_sim_ids": [],
        "source_user_ids": [],
        "evidence_event_ids": [],
        "confidence_score": "0.9",
        "importance_score": "0.8",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })


def _seed_sim_event(aws_mock, project_id: str = "proj-1", sprint_id: str = "sprint-1"):
    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("SimEvents")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": "USER#alice",
        "sk": f"EVT#{now}#sim-1#status_change#evt-001",
        "gsi1pk": "SIM#sim-1",
        "gsi1sk": f"EVT#{now}",
        "gsi2pk": f"PROJECT#{project_id}",
        "gsi2sk": f"EVT#{now}",
        "entity_type": "sim_event",
        "event_id": "evt-001",
        "source": "sim",
        "user_id": "alice",
        "sprint_id": sprint_id,
        "sim_id": "sim-1",
        "sim_title": "TICKET-101",
        "event_type": "status_change",
        "event_time": now,
        "actor_user_id": "alice",
        "actor_type": "developer",
        "content": {"description": "Status changed from In Progress to Done"},
        "metadata": {},
        "created_at": now,
    })


# ── Tests: GET /projects ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_projects_empty(client: AsyncClient):
    """Returns empty list when no project contexts exist for the sprint."""
    response = await client.get("/api/v1/projects", params={"sprintId": "sprint-empty"})
    assert response.status_code == 200
    data = response.json()
    assert data["sprint_id"] == "sprint-empty"
    assert data["projects"] == []


@pytest.mark.asyncio
async def test_list_projects_with_data(client: AsyncClient, aws_mock):
    """Returns project list when ProjectSprintContext items exist."""
    _seed_project_sprint_context(aws_mock)
    response = await client.get("/api/v1/projects", params={"sprintId": "sprint-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["sprint_id"] == "sprint-1"
    assert len(data["projects"]) >= 1
    project = data["projects"][0]
    assert project["project_id"] == "proj-1"
    assert project["health"] in ("GREEN", "green", "YELLOW", "yellow", "RED", "red", "unknown")


# ── Tests: GET /projects/{projectId}/sprint-context ───────────────────────

@pytest.mark.asyncio
async def test_sprint_context_empty(client: AsyncClient):
    """Returns fallback when no context exists."""
    response = await client.get(
        "/api/v1/projects/no-such-project/sprint-context",
        params={"sprintId": "sprint-99"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "no-such-project"
    assert "context_summary" in data


@pytest.mark.asyncio
async def test_sprint_context_with_data(client: AsyncClient, aws_mock):
    """Returns real context when ProjectSprintContext exists."""
    _seed_project_sprint_context(aws_mock)
    response = await client.get(
        "/api/v1/projects/proj-1/sprint-context",
        params={"sprintId": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert data["sprint_id"] == "sprint-1"
    assert len(data["context_summary"]) > 0


# ── Tests: GET /projects/{projectId}/facts ────────────────────────────────

@pytest.mark.asyncio
async def test_project_facts_empty(client: AsyncClient):
    """Returns empty facts list when no facts exist."""
    response = await client.get(
        "/api/v1/projects/no-such-project/facts",
        params={"sprintId": "sprint-99"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["facts"] == []


@pytest.mark.asyncio
async def test_project_facts_with_data(client: AsyncClient, aws_mock):
    """Returns facts when ProjectFacts items exist."""
    _seed_project_fact(aws_mock)
    response = await client.get(
        "/api/v1/projects/proj-1/facts",
        params={"sprintId": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert len(data["facts"]) >= 1
    fact = data["facts"][0]
    assert fact["fact_id"] == "fact-001"
    assert fact["category"] == "blocker"


# ── Tests: GET /projects/{projectId}/timeline ─────────────────────────────

@pytest.mark.asyncio
async def test_timeline_empty(client: AsyncClient):
    """Returns empty events list when no sim events exist."""
    response = await client.get(
        "/api/v1/projects/no-such-project/timeline",
        params={"sprintId": "sprint-99"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []


@pytest.mark.asyncio
async def test_timeline_with_data(client: AsyncClient, aws_mock):
    """Returns events when SimEvents exist for the project."""
    _seed_sim_event(aws_mock)
    response = await client.get(
        "/api/v1/projects/proj-1/timeline",
        params={"sprintId": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "proj-1"
    assert len(data["events"]) >= 1
    event = data["events"][0]
    assert event["event_type"] == "status_change"


# ── Tests: GET /leadership/roadmap-summary ────────────────────────────────

@pytest.mark.asyncio
async def test_roadmap_summary_empty(client: AsyncClient):
    """Returns fallback when no project contexts exist for the sprint."""
    response = await client.get(
        "/api/v1/leadership/roadmap-summary",
        params={"sprintId": "sprint-empty"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sprint_id"] == "sprint-empty"
    assert "summary" in data


@pytest.mark.asyncio
async def test_roadmap_summary_with_data(client: AsyncClient, aws_mock):
    """Returns aggregated roadmap summary when project contexts exist."""
    _seed_project_sprint_context(aws_mock)
    response = await client.get(
        "/api/v1/leadership/roadmap-summary",
        params={"sprintId": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sprint_id"] == "sprint-1"
    assert len(data["summary"]) > 0
    assert data["health_overview"] in ("green", "yellow", "red")
