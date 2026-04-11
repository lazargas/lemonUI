"""
Standup Cache Service
---------------------
Pre-generates standup summaries for a list of developers and stores them
in the StandupCache DynamoDB table so they can be served instantly at
standup time with zero LLM latency.

Table: StandupCache
  pk  = USER#<userId>
  sk  = SPRINT#<sprintId>
  gsi1pk = SPRINT#<sprintId>   gsi1sk = USER#<userId>
  gsi2pk = JOB#<jobId>         gsi2sk = USER#<userId>

Flow:
  POST /standup/trigger  → fire-and-forget background task
    1. For each alias, call get_standup_helper() (same logic as the live API)
    2. Store the result in StandupCache
    3. Track job_id, status, timestamps

  GET /standup/cached?userId=&sprintId=  → instant DynamoDB read
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import boto3

from app.core.config import settings
from app.schemas.developer import CachedStandupResponse, StandupTriggerResponse
from app.services.developer_service import DeveloperService
from app.utils.logger import logger

_STANDUP_CACHE_TABLE = "StandupCache"
_USER_PREFIX = "USER#"
_SPRINT_PREFIX = "SPRINT#"
_JOB_PREFIX = "JOB#"


def _get_table():
    ddb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return ddb.Table(_STANDUP_CACHE_TABLE)  # type: ignore[attr-defined]


class StandupCacheService:

    def __init__(self) -> None:
        self._dev_service = DeveloperService()

    # ── Trigger (fire-and-forget) ──────────────────────────────────────────

    def trigger(self, aliases: List[str], sprint_id: str) -> StandupTriggerResponse:
        """
        Kick off background generation for all aliases.
        Returns immediately with a job_id — generation runs in the background.
        """
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[standup-cache] Trigger job_id={job_id} sprint_id={sprint_id} "
            f"aliases={aliases}"
        )

        # Write a "pending" placeholder for each alias so callers can poll
        table = _get_table()
        for alias in aliases:
            table.put_item(Item={
                "pk": f"{_USER_PREFIX}{alias}",
                "sk": f"{_SPRINT_PREFIX}{sprint_id}",
                "gsi1pk": f"{_SPRINT_PREFIX}{sprint_id}",
                "gsi1sk": f"{_USER_PREFIX}{alias}",
                "gsi2pk": f"{_JOB_PREFIX}{job_id}",
                "gsi2sk": f"{_USER_PREFIX}{alias}",
                "user_id": alias,
                "sprint_id": sprint_id,
                "job_id": job_id,
                "status": "pending",
                "started_at": started_at,
                "suggested_talking_points": [],
                "risks_to_mention": [],
                "blockers": [],
                "pending_items": [],
                "generated_at": "",
                "error": None,
            })

        # Schedule the async generation in the background
        asyncio.create_task(
            self._generate_all(aliases=aliases, sprint_id=sprint_id, job_id=job_id)
        )

        return StandupTriggerResponse(
            job_id=job_id,
            sprint_id=sprint_id,
            aliases=aliases,
            started_at=started_at,
            status="started",
        )

    async def _generate_all(
        self, aliases: List[str], sprint_id: str, job_id: str
    ) -> None:
        """
        Generate standup summaries for all aliases sequentially and store each
        result in StandupCache as it completes.
        """
        table = _get_table()

        for alias in aliases:
            logger.info(
                f"[standup-cache] Generating for alias={alias} sprint_id={sprint_id} "
                f"job_id={job_id}"
            )
            try:
                result = await self._dev_service.get_standup_helper(
                    user_id=alias, sprint_id=sprint_id
                )
                table.update_item(
                    Key={
                        "pk": f"{_USER_PREFIX}{alias}",
                        "sk": f"{_SPRINT_PREFIX}{sprint_id}",
                    },
                    UpdateExpression=(
                        "SET #status = :s, "
                        "suggested_talking_points = :tp, "
                        "risks_to_mention = :rm, "
                        "blockers = :bl, "
                        "pending_items = :pi, "
                        "generated_at = :ga, "
                        "#err = :e"
                    ),
                    ExpressionAttributeNames={
                        "#status": "status",
                        "#err": "error",
                    },
                    ExpressionAttributeValues={
                        ":s": "completed",
                        ":tp": result.suggested_talking_points,
                        ":rm": result.risks_to_mention,
                        ":bl": result.blockers,
                        ":pi": result.pending_items,
                        ":ga": result.generated_at,
                        ":e": None,
                    },
                )
                logger.info(
                    f"[standup-cache] ✓ alias={alias} sprint_id={sprint_id}"
                )
            except Exception as exc:
                logger.error(
                    f"[standup-cache] ✗ alias={alias} sprint_id={sprint_id} error={exc}"
                )
                table.update_item(
                    Key={
                        "pk": f"{_USER_PREFIX}{alias}",
                        "sk": f"{_SPRINT_PREFIX}{sprint_id}",
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

        logger.info(
            f"[standup-cache] Job complete job_id={job_id} sprint_id={sprint_id} "
            f"total={len(aliases)}"
        )

    # ── Fetch cached standup ───────────────────────────────────────────────

    def get_cached(
        self, user_id: str, sprint_id: str
    ) -> Optional[CachedStandupResponse]:
        """
        Fetch a pre-generated standup from StandupCache.
        Returns None if no cache entry exists for this user+sprint.
        """
        table = _get_table()
        resp = table.get_item(
            Key={
                "pk": f"{_USER_PREFIX}{user_id}",
                "sk": f"{_SPRINT_PREFIX}{sprint_id}",
            }
        )
        item = resp.get("Item")
        if not item:
            return None

        return CachedStandupResponse(
            user_id=item.get("user_id", user_id),
            sprint_id=item.get("sprint_id", sprint_id),
            suggested_talking_points=item.get("suggested_talking_points", []),
            risks_to_mention=item.get("risks_to_mention", []),
            blockers=item.get("blockers", []),
            pending_items=item.get("pending_items", []),
            generated_at=item.get("generated_at", ""),
            job_id=item.get("job_id", ""),
            status=item.get("status", "unknown"),
            error=item.get("error"),
        )
