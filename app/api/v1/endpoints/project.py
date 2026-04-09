"""
Project Endpoints
-----------------
GET /api/v1/projects/{projectId}/sprint-context  – sprint context summary
GET /api/v1/projects/{projectId}/facts           – project facts (blockers, risks, etc.)
GET /api/v1/projects                             – list all projects for a sprint
GET /api/v1/projects/{projectId}/timeline        – event timeline
"""
from fastapi import APIRouter, Path, Query

from app.schemas.project import (
    ProjectFactsResponse,
    ProjectsListResponse,
    SprintContextResponse,
    TimelineResponse,
)
from app.services.project_service import ProjectService

router = APIRouter()
_svc = ProjectService()


@router.get(
    "",
    response_model=ProjectsListResponse,
    summary="List all projects for a sprint",
    description="Returns a list of all projects with their health and summary for the given sprint.",
)
async def list_projects(
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.list_projects(sprint_id=sprintId)


@router.get(
    "/{projectId}/sprint-context",
    response_model=SprintContextResponse,
    summary="Get sprint context for a project",
    description="Returns the precomputed sprint context summary for the given project and sprint.",
)
async def get_sprint_context(
    projectId: str = Path(..., description="Project ID"),
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.get_sprint_context(project_id=projectId, sprint_id=sprintId)


@router.get(
    "/{projectId}/facts",
    response_model=ProjectFactsResponse,
    summary="Get project facts for a sprint",
    description=(
        "Returns structured project facts for the given project and sprint. "
        "Facts include blockers, risks, dependencies, and decisions."
    ),
)
async def get_project_facts(
    projectId: str = Path(..., description="Project ID"),
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.get_project_facts(project_id=projectId, sprint_id=sprintId)


@router.get(
    "/{projectId}/timeline",
    response_model=TimelineResponse,
    summary="Get event timeline for a project",
    description=(
        "Returns a chronological list of important events for the given project "
        "and sprint (status changes, blockers added, decisions made, etc.)."
    ),
)
async def get_timeline(
    projectId: str = Path(..., description="Project ID"),
    sprintId: str = Query(..., description="Sprint ID"),
):
    return await _svc.get_timeline(project_id=projectId, sprint_id=sprintId)
