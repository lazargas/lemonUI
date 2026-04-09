"""
test_ingestion.py
-----------------
Tests for the Ingestion API endpoints:
  POST /api/v1/ingestion/trigger
  GET  /api/v1/ingestion/status/{jobId}
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_ingestion_default(client: AsyncClient):
    """Trigger with default source returns a queued job."""
    response = await client.post("/api/v1/ingestion/trigger", json={})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["source"] == "taskei"
    assert data["records_processed"] == 0
    assert "started_at" in data


@pytest.mark.asyncio
async def test_trigger_ingestion_with_filters(client: AsyncClient):
    """Trigger with user_id and sprint_id filters."""
    response = await client.post(
        "/api/v1/ingestion/trigger",
        json={"source": "taskei", "user_id": "alice", "sprint_id": "sprint-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["source"] == "taskei"


@pytest.mark.asyncio
async def test_ingestion_status_unknown(client: AsyncClient):
    """Status for an unknown job_id returns 'unknown' status."""
    response = await client.get("/api/v1/ingestion/status/non-existent-job-id")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "non-existent-job-id"
    assert data["status"] == "unknown"


@pytest.mark.asyncio
async def test_trigger_then_check_status(client: AsyncClient):
    """Trigger a job, then check its status using the returned job_id."""
    trigger_resp = await client.post("/api/v1/ingestion/trigger", json={})
    assert trigger_resp.status_code == 200
    job_id = trigger_resp.json()["job_id"]

    status_resp = await client.get(f"/api/v1/ingestion/status/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    # Job tracking not yet persisted, so status is 'unknown' — but job_id matches
    assert data["job_id"] == job_id
