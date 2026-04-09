"""
Project Service
---------------
Handles sprint context, project facts, project list, timeline,
and leadership roadmap summary logic.

All DynamoDB reads are wired to the sprint_memory persistence layer.
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
from app.sprint_memory.persistence.project_facts_accessor import ProjectFactsAccessor
from app.sprint_memory.persistence.project_sprint_context_accessor import ProjectSprintContextAccessor
from app.sprint_memory.persistence.projects_accessor import ProjectsAccessor
from app.sprint_memory.persistence.sim_events_accessor import SimEventsAccessor
from app.utils.logger import logger


class ProjectService:

    def __init__(self) -> None:
        self._facts_accessor = ProjectFactsAccessor()
        self._context_accessor = ProjectSprintContextAccessor()
        self._projects_accessor = ProjectsAccessor()
        self._events_accessor = SimEventsAccessor()

    # ── Sprint Context ─────────────────────────────────────────────────────

    async def get_sprint_context(
        self, project_id: str, sprint_id: str
    ) -> SprintContextResponse:
        logger.info(
            f"Fetching sprint context project_id={project_id} sprint_id={sprint_id}"
        )

        record = self._context_accessor.get_context(project_id, sprint_id)

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

        # Build a human-readable context summary from the rich model
        summary_parts: List[str] = []
        if record.summary.overall_status:
            summary_parts.append(f"Status: {record.summary.overall_status}")
        if record.summary.health:
            summary_parts.append(f"Health: {record.summary.health}")
        if record.leadership_summary.one_liner:
            summary_parts.append(record.leadership_summary.one_liner)
        if record.blockers:
            summary_parts.append(f"Blockers: {'; '.join(record.blockers)}")
        if record.risks:
            risk_strs = [r.summary for r in record.risks]
            summary_parts.append(f"Risks: {'; '.join(risk_strs)}")

        context_summary = " | ".join(summary_parts) if summary_parts else (
            f"Sprint context available for project {project_id} sprint {sprint_id}."
        )

        return SprintContextResponse(
            project_id=project_id,
            sprint_id=sprint_id,
            context_summary=context_summary,
            generated_at=record.last_refreshed_at,
        )

    # ── Project Facts ──────────────────────────────────────────────────────

    async def get_project_facts(
        self, project_id: str, sprint_id: str
    ) -> ProjectFactsResponse:
        logger.info(
            f"Fetching project facts project_id={project_id} sprint_id={sprint_id}"
        )

        raw_facts = self._facts_accessor.query_by_project(
            project_id=project_id, active_only=True, limit=100
        )

        # Filter to the requested sprint
        sprint_facts = [f for f in raw_facts if f.sprint_id == sprint_id]

        facts: List[ProjectFact] = [
            ProjectFact(
                fact_id=f.fact_id,
                project_id=f.project_id,
                sprint_id=f.sprint_id,
                category=f.fact_type,
                content=f.summary,
                recorded_at=f.created_at,
            )
            for f in sprint_facts
        ]

        return ProjectFactsResponse(
            project_id=project_id,
            sprint_id=sprint_id,
            facts=facts,
        )

    # ── Projects List ──────────────────────────────────────────────────────

    async def list_projects(self, sprint_id: str) -> ProjectsListResponse:
        logger.info(f"Listing projects for sprint_id={sprint_id}")

        # Query all project sprint contexts for this sprint via GSI1
        # (gsi1pk = SPRINT#<sprintId>)
        from boto3.dynamodb.conditions import Key
        from app.sprint_memory.constants import SPRINT_PREFIX

        gsi1pk = f"{SPRINT_PREFIX}{sprint_id}"
        resp = self._context_accessor.table.query(
            IndexName="gsi1pk-gsi1sk-index",
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
            Limit=100,
        )

        from app.sprint_memory.models.project_sprint_context import ProjectSprintContextItem

        projects: List[ProjectSummary] = []
        for item in resp.get("Items", []):
            try:
                ctx = ProjectSprintContextItem(**item)
                projects.append(
                    ProjectSummary(
                        project_id=ctx.project_id,
                        project_name=ctx.project_name or ctx.project_id,
                        sprint_id=ctx.sprint_id,
                        health=ctx.summary.health or "unknown",
                        summary=ctx.leadership_summary.one_liner or ctx.summary.overall_status or "",
                    )
                )
            except Exception as exc:
                logger.warning(f"Skipping malformed project context item: {exc}")

        return ProjectsListResponse(sprint_id=sprint_id, projects=projects)

    # ── Timeline ───────────────────────────────────────────────────────────

    async def get_timeline(
        self, project_id: str, sprint_id: str
    ) -> TimelineResponse:
        logger.info(
            f"Fetching timeline project_id={project_id} sprint_id={sprint_id}"
        )

        # Query SimEvents by project via GSI2 (gsi2pk = PROJECT#<projectId>)
        from boto3.dynamodb.conditions import Key
        from app.sprint_memory.constants import PROJECT_PREFIX
        from app.sprint_memory.models.sim_event import SimEventItem

        gsi2pk = f"{PROJECT_PREFIX}{project_id}"
        resp = self._events_accessor.table.query(
            IndexName="gsi2pk-gsi2sk-index",
            KeyConditionExpression=Key("gsi2pk").eq(gsi2pk),
            ScanIndexForward=False,
            Limit=100,
        )

        events: List[TimelineEvent] = []
        for item in resp.get("Items", []):
            try:
                ev = SimEventItem(**item)
                if ev.sprint_id != sprint_id:
                    continue
                events.append(
                    TimelineEvent(
                        event_id=ev.event_id,
                        project_id=project_id,
                        sprint_id=ev.sprint_id,
                        event_type=ev.event_type,
                        description=(
                            ev.content.get("description", "")
                            or ev.content.get("title", "")
                            or ev.event_type
                        ),
                        occurred_at=ev.event_time,
                    )
                )
            except Exception as exc:
                logger.warning(f"Skipping malformed sim event item: {exc}")

        return TimelineResponse(
            project_id=project_id,
            sprint_id=sprint_id,
            events=events,
        )

    # ── Leadership Roadmap Summary ─────────────────────────────────────────

    async def get_roadmap_summary(self, sprint_id: str) -> RoadmapSummaryResponse:
        logger.info(f"Fetching roadmap summary for sprint_id={sprint_id}")

        # Aggregate all project sprint contexts for this sprint
        from boto3.dynamodb.conditions import Key
        from app.sprint_memory.constants import SPRINT_PREFIX
        from app.sprint_memory.models.project_sprint_context import ProjectSprintContextItem

        gsi1pk = f"{SPRINT_PREFIX}{sprint_id}"
        resp = self._context_accessor.table.query(
            IndexName="gsi1pk-gsi1sk-index",
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
            Limit=100,
        )

        all_risks: List[str] = []
        all_deps: List[str] = []
        health_counts: Dict[str, int] = {"GREEN": 0, "YELLOW": 0, "RED": 0}
        summaries: List[str] = []

        for item in resp.get("Items", []):
            try:
                ctx = ProjectSprintContextItem(**item)
                for r in ctx.risks:
                    all_risks.append(f"[{ctx.project_name or ctx.project_id}] {r.summary}")
                for d in ctx.dependencies:
                    all_deps.append(f"[{ctx.project_name or ctx.project_id}] {d.summary}")
                h = ctx.summary.health.upper()
                if h in health_counts:
                    health_counts[h] += 1
                if ctx.leadership_summary.one_liner:
                    summaries.append(
                        f"{ctx.project_name or ctx.project_id}: {ctx.leadership_summary.one_liner}"
                    )
            except Exception as exc:
                logger.warning(f"Skipping malformed project context item: {exc}")

        if not summaries:
            return RoadmapSummaryResponse(
                sprint_id=sprint_id,
                summary=f"No roadmap summary has been generated yet for sprint {sprint_id}.",
                risks=[],
                dependencies=[],
                health_overview="unknown",
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # Determine overall health
        if health_counts["RED"] > 0:
            health_overview = "red"
        elif health_counts["YELLOW"] > 0:
            health_overview = "yellow"
        else:
            health_overview = "green"

        summary = f"Sprint {sprint_id} — " + " | ".join(summaries)

        return RoadmapSummaryResponse(
            sprint_id=sprint_id,
            summary=summary,
            risks=all_risks[:10],
            dependencies=all_deps[:10],
            health_overview=health_overview,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
