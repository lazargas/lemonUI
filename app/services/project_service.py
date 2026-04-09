"""
Project Service
---------------
Handles sprint context, project facts, project list, timeline,
and leadership roadmap summary logic.

NOTE: DB repository calls are stubbed with TODO markers.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.project import (
    ProjectFact,
    ProjectFactsResponse,
    ProjectsListResponse,
    ProjectSummary,
    RoadmapSummaryResponse,
    SprintContextResponse,
    TimelineEvent,
    TimelineResponse,
)
from app.utils.logger import logger


class ProjectService:

    # ── Sprint Context ─────────────────────────────────────────────────────

    async def get_sprint_context(
        self, project_id: str, sprint_id: str
    ) -> SprintContextResponse:
        logger.info(
            f"Fetching sprint context project_id={project_id} sprint_id={sprint_id}"
        )

        # TODO: fetch from DynamoDB
        # record = await sprint_context_repo.get(project_id, sprint_id)
        record: Optional[Dict[str, Any]] = None

        if record is None:
            return SprintContextResponse(
                project_id=project_id,
                sprint_id=sprint_id,
                context_summary=(
                    f"No sprint context has been generated yet for project "
                    f"{project_id} sprint {sprint_id}."
                ),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        return SprintContextResponse(**record)

    # ── Project Facts ──────────────────────────────────────────────────────

    async def get_project_facts(
        self, project_id: str, sprint_id: str
    ) -> ProjectFactsResponse:
        logger.info(
            f"Fetching project facts project_id={project_id} sprint_id={sprint_id}"
        )

        # TODO: fetch from DynamoDB
        # facts = await project_facts_repo.list(project_id, sprint_id)
        facts: List[ProjectFact] = []

        return ProjectFactsResponse(
            project_id=project_id,
            sprint_id=sprint_id,
            facts=facts,
        )

    # ── Projects List ──────────────────────────────────────────────────────

    async def list_projects(self, sprint_id: str) -> ProjectsListResponse:
        logger.info(f"Listing projects for sprint_id={sprint_id}")

        # TODO: fetch from DynamoDB
        # projects = await project_repo.list_by_sprint(sprint_id)
        projects: List[ProjectSummary] = []

        return ProjectsListResponse(sprint_id=sprint_id, projects=projects)

    # ── Timeline ───────────────────────────────────────────────────────────

    async def get_timeline(
        self, project_id: str, sprint_id: str
    ) -> TimelineResponse:
        logger.info(
            f"Fetching timeline project_id={project_id} sprint_id={sprint_id}"
        )

        # TODO: fetch from DynamoDB
        # events = await timeline_repo.list(project_id, sprint_id)
        events: List[TimelineEvent] = []

        return TimelineResponse(
            project_id=project_id,
            sprint_id=sprint_id,
            events=events,
        )

    # ── Leadership Roadmap Summary ─────────────────────────────────────────

    async def get_roadmap_summary(self, sprint_id: str) -> RoadmapSummaryResponse:
        logger.info(f"Fetching roadmap summary for sprint_id={sprint_id}")

        # TODO: fetch precomputed summary from DynamoDB
        # record = await roadmap_summary_repo.get(sprint_id)
        record: Optional[Dict[str, Any]] = None

        if record is None:
            return RoadmapSummaryResponse(
                sprint_id=sprint_id,
                summary=(
                    f"No roadmap summary has been generated yet for sprint {sprint_id}."
                ),
                risks=[],
                dependencies=[],
                health_overview="unknown",
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        return RoadmapSummaryResponse(**record)
