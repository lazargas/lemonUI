"""
Standup Cache Endpoints
-----------------------
POST /api/v1/standup/trigger  – fire-and-forget bulk pre-generation
GET  /api/v1/standup/cached   – instant fetch from StandupCache DynamoDB
"""
from fastapi import APIRouter, HTTPException, Query

from app.schemas.developer import (
    CachedStandupResponse,
    StandupTriggerRequest,
    StandupTriggerResponse,
)
from app.services.standup_cache_service import StandupCacheService

router = APIRouter()
_svc = StandupCacheService()


@router.post(
    "/trigger",
    response_model=StandupTriggerResponse,
    summary="Trigger bulk standup pre-generation (fire-and-forget)",
    description=(
        "Accepts a list of developer aliases and a sprint ID. "
        "Immediately returns a job_id and starts generating standup summaries "
        "for each alias in the background using the same logic as /standup-helper. "
        "Results are stored in StandupCache DynamoDB and can be fetched instantly "
        "via GET /standup/cached. "
        "Intended to be called ~15 minutes before standup (e.g. 11:45 AM for a 12 PM standup)."
    ),
)
async def trigger_standup_generation(body: StandupTriggerRequest):
    if not body.aliases:
        raise HTTPException(status_code=400, detail="aliases list cannot be empty")
    if not body.sprint_id:
        raise HTTPException(status_code=400, detail="sprint_id is required")

    return _svc.trigger(aliases=body.aliases, sprint_id=body.sprint_id)


@router.get(
    "/cached",
    response_model=CachedStandupResponse,
    summary="Fetch pre-generated standup from cache (instant, no LLM call)",
    description=(
        "Returns the pre-generated standup summary for a developer from StandupCache. "
        "This is a direct DynamoDB read — no LLM call, sub-10ms latency. "
        "The `status` field indicates: 'completed' (ready), 'pending' (still generating), "
        "or 'failed' (generation error, check `error` field). "
        "Call POST /standup/trigger first to populate the cache."
    ),
)
async def get_cached_standup(
    userId: str = Query(..., description="Developer alias / user ID"),
    sprintId: str = Query(..., description="Sprint ID"),
):
    result = _svc.get_cached(user_id=userId, sprint_id=sprintId)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No cached standup found for userId={userId} sprintId={sprintId}. "
                "Call POST /standup/trigger first."
            ),
        )
    return result
