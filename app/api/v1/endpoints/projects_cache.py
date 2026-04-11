"""
Projects Cache Endpoints
------------------------
POST /api/v1/projects/trigger  – fire-and-forget bulk pre-generation for a sprint
GET  /api/v1/projects/cached   – instant fetch from ProjectsCache DynamoDB
"""
from fastapi import APIRouter, HTTPException, Query

from app.schemas.project import (
    CachedProjectsResponse,
    ProjectsCacheTriggerRequest,
    ProjectsCacheTriggerResponse,
)
from app.services.projects_cache_service import ProjectsCacheService

router = APIRouter()
_svc = ProjectsCacheService()


@router.post(
    "/trigger",
    response_model=ProjectsCacheTriggerResponse,
    summary="Trigger bulk project list pre-generation (fire-and-forget)",
    description=(
        "Accepts a sprint ID and immediately starts generating the full projects list "
        "(with LLM summaries, health, progress) in the background. "
        "Returns a job_id instantly — generation runs asynchronously. "
        "Results are stored in ProjectsCache DynamoDB and can be fetched instantly "
        "via GET /projects/cached. "
        "Intended to be called before leadership reviews or dashboard loads."
    ),
)
async def trigger_projects_generation(body: ProjectsCacheTriggerRequest):
    if not body.sprint_id:
        raise HTTPException(status_code=400, detail="sprint_id is required")
    return _svc.trigger(sprint_id=body.sprint_id)


@router.get(
    "/cached",
    response_model=CachedProjectsResponse,
    summary="Fetch pre-generated projects list from cache (instant, no LLM call)",
    description=(
        "Returns the pre-generated projects list for a sprint from ProjectsCache. "
        "This is a direct DynamoDB read — no LLM call, sub-10ms latency. "
        "The `status` field indicates: 'completed' (ready), 'pending' (still generating), "
        "or 'failed' (generation error, check `error` field). "
        "Call POST /projects/trigger first to populate the cache."
    ),
)
async def get_cached_projects(
    sprintId: str = Query(..., description="Sprint ID"),
):
    result = _svc.get_cached(sprint_id=sprintId)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No cached projects found for sprintId={sprintId}. "
                "Call POST /projects/trigger first."
            ),
        )
    return result
