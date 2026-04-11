"""
Projects Cache Service
----------------------
Pre-generates the full projects list (with LLM summaries) for a sprint and
stores it in the ProjectsCache DynamoDB table so it can be served instantly
with zero LLM latency.

Table: ProjectsCache
  pk  = SPRINT#<sprintId>
  sk  = METADATA
  gsi1pk = JOB#<jobId>   gsi1sk = SPRINT#<sprintId>

Flow:
  POST /projects/trigger  → fire-and-forget background task
    1. Call project_service.list_projects() (same logic as the live API)
    2. Store the full result in ProjectsCache
    3. Track job_id, status, timestamps

  GET /projects/cached?sprintId=  → instant DynamoDB read
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import boto3

from app.core.config import settings
from app.schemas.project import (
    CachedProjectsResponse,
    ProjectSummary,
    ProjectsCacheTriggerResponse,
)
from app.utils.logger import logger

_PROJECTS_CACHE_TABLE = "ProjectsCache"
_SPRINT_PREFIX = "SPRINT#"
_JOB_PREFIX = "JOB#"
_METADATA_SK = "METADATA"


def _get_table():
    ddb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return ddb.Table(_PROJECTS_CACHE_TABLE)  # type: ignore[attr-defined]


def _serialize_projects(projects: List[ProjectSummary]) -> list:
    """Convert ProjectSummary list to plain dicts for DynamoDB storage."""
    return [
        {
            "project_id": p.project_id,
            "project_name": p.project_name,
            "sprint_id": p.sprint_id,
            "health": p.health,
            "summary": p.summary,
            "progress": p.progress,
            "sims": [
                {
                    "sim_id": s.sim_id,
                    "title": s.title,
                    "status": s.status,
                    "owner": s.owner,
                }
                for s in p.sims
            ],
            "developers": p.developers,
        }
        for p in projects
    ]


def _deserialize_projects(raw: list) -> List[ProjectSummary]:
    """Reconstruct ProjectSummary list from DynamoDB dicts."""
    from app.schemas.project import SimItem
    result = []
    for item in raw:
        result.append(ProjectSummary(
            project_id=item.get("project_id", ""),
            project_name=item.get("project_name", ""),
            sprint_id=item.get("sprint_id", ""),
            health=item.get("health", "unknown"),
            summary=item.get("summary", ""),
            progress=int(item.get("progress", 0)),
            sims=[
                SimItem(
                    sim_id=s.get("sim_id", ""),
                    title=s.get("title", ""),
                    status=s.get("status", ""),
                    owner=s.get("owner", ""),
                )
                for s in item.get("sims", [])
            ],
            developers=item.get("developers", []),
        ))
    return result


class ProjectsCacheService:

    # ── Trigger (fire-and-forget) ──────────────────────────────────────────

    def trigger(self, sprint_id: str) -> ProjectsCacheTriggerResponse:
        """
        Kick off background generation for the given sprint.
        Returns immediately with a job_id.
        """

        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[projects-cache] Trigger job_id={job_id} sprint_id={sprint_id}"
        )

        # Write a "pending" placeholder immediately
        table = _get_table()
        table.put_item(Item={
            "pk": f"{_SPRINT_PREFIX}{sprint_id}",
            "sk": _METADATA_SK,
            "gsi1pk": f"{_JOB_PREFIX}{job_id}",
            "gsi1sk": f"{_SPRINT_PREFIX}{sprint_id}",
            "sprint_id": sprint_id,
            "job_id": job_id,
            "status": "pending",
            "started_at": started_at,
            "projects": [],
            "generated_at": "",
            "error": None,
        })

        # Schedule async generation in background
        asyncio.create_task(
            self._generate(sprint_id=sprint_id, job_id=job_id)
        )

        return ProjectsCacheTriggerResponse(
            job_id=job_id,
            sprint_id=sprint_id,
            started_at=started_at,
            status="started",
        )

    async def _generate(self, sprint_id: str, job_id: str) -> None:
        """
        Generate the full projects list and store it in ProjectsCache.
        """
        from app.services.project_service import ProjectService

        table = _get_table()
        svc = ProjectService()

        logger.info(
            f"[projects-cache] Generating sprint_id={sprint_id} job_id={job_id}"
        )
        try:
            result = await svc.list_projects(sprint_id=sprint_id)
            serialized = _serialize_projects(result.projects)
            generated_at = datetime.now(timezone.utc).isoformat()

            table.update_item(
                Key={
                    "pk": f"{_SPRINT_PREFIX}{sprint_id}",
                    "sk": _METADATA_SK,
                },
                UpdateExpression=(
                    "SET #status = :s, projects = :p, "
                    "generated_at = :ga, #err = :e"
                ),
                ExpressionAttributeNames={
                    "#status": "status",
                    "#err": "error",
                },
                ExpressionAttributeValues={
                    ":s": "completed",
                    ":p": serialized,
                    ":ga": generated_at,
                    ":e": None,
                },
            )
            logger.info(
                f"[projects-cache] ✓ sprint_id={sprint_id} "
                f"projects={len(result.projects)}"
            )
        except Exception as exc:
            logger.error(
                f"[projects-cache] ✗ sprint_id={sprint_id} error={exc}"
            )
            table.update_item(
                Key={
                    "pk": f"{_SPRINT_PREFIX}{sprint_id}",
                    "sk": _METADATA_SK,
                },
                UpdateExpression="SET #status = :s, #err = :e",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#err": "error",
                },
                ExpressionAttributeValues={
                    ":s": "failed",
                    ":e": str(exc),
                },
            )

    # ── Fetch cached projects ──────────────────────────────────────────────

    def get_cached(self, sprint_id: str) -> Optional[CachedProjectsResponse]:
        """
        Fetch the pre-generated projects list from ProjectsCache.
        Returns None if no cache entry exists for this sprint.
        """
        table = _get_table()
        resp = table.get_item(
            Key={
                "pk": f"{_SPRINT_PREFIX}{sprint_id}",
                "sk": _METADATA_SK,
            }
        )
        item = resp.get("Item")
        if not item:
            return None

        projects = _deserialize_projects(item.get("projects", []))

        return CachedProjectsResponse(
            sprint_id=item.get("sprint_id", sprint_id),
            projects=projects,
            generated_at=item.get("generated_at", ""),
            job_id=item.get("job_id", ""),
            status=item.get("status", "unknown"),
            error=item.get("error"),
        )
