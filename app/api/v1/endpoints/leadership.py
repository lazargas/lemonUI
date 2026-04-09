"""
Leadership Endpoints
--------------------
GET /api/v1/leadership/roadmap-summary  – executive roadmap summary for a sprint
"""
from fastapi import APIRouter, Query

from app.schemas.project import RoadmapSummaryResponse
from app.services.project_service import ProjectService

router = APIRouter()
_svc = ProjectService()


@router.get(
    "/roadmap-summary",
    response_model=RoadmapSummaryResponse,
    summary="Get leadership roadmap summary",
    description=(
        "Returns a concise, executive-level roadmap summary for the given sprint. "
        "Includes major risks, dependencies, and overall project health. "
        "This output is precomputed by a scheduled background job."
    ),
)
async def get_roadmap_summary(
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.get_roadmap_summary(sprint_id=sprintId)
