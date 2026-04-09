"""
Jobs Endpoints
--------------
Manual triggers for summary generation jobs (useful for dev/testing).
In production these are triggered by EventBridge schedules.

POST /api/v1/jobs/daily-summary         – trigger daily summary for a developer
POST /api/v1/jobs/sprint-summary        – trigger sprint summary for a developer
POST /api/v1/jobs/roadmap-summary       – trigger roadmap summary for a sprint
"""
from fastapi import APIRouter, Query

from app.services.summary_job_service import SummaryJobService

router = APIRouter()
_svc = SummaryJobService()


@router.post(
    "/daily-summary",
    summary="Trigger daily summary generation",
    description=(
        "Manually triggers the daily summary generation job for a developer. "
        "In production this runs automatically on a daily schedule."
    ),
)
async def trigger_daily_summary(
    userId: str = Query(..., description="Developer user ID"),
):
    return await _svc.trigger_daily_summary(user_id=userId)


@router.post(
    "/sprint-summary",
    summary="Trigger sprint summary generation",
    description=(
        "Manually triggers the sprint summary generation job for a developer and sprint."
    ),
)
async def trigger_sprint_summary(
    userId: str = Query(..., description="Developer user ID"),
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.trigger_sprint_summary(user_id=userId, sprint_id=sprintId)


@router.post(
    "/roadmap-summary",
    summary="Trigger roadmap summary generation",
    description=(
        "Manually triggers the leadership roadmap summary generation job for a sprint."
    ),
)
async def trigger_roadmap_summary(
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.trigger_roadmap_summary(sprint_id=sprintId)
