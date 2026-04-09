"""
Summary Job Service
-------------------
Handles on-demand triggering of summary generation jobs
(daily summary, sprint summary, roadmap summary).

In production these run on a schedule (EventBridge / cron).
This service allows manual triggering via API for dev/testing.

Flow per job:
  1. Fetch activity / context data from DynamoDB
  2. Render a prompt
  3. Call Claude 3 Sonnet on Bedrock
  4. Store the result back in DynamoDB (UserSprintContext / ProjectSprintContext)
"""
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.llm.llm_service import generate
from app.llm.prompts import (
    DAILY_SUMMARY_PROMPT,
    SPRINT_SUMMARY_PROMPT,
    ROADMAP_SUMMARY_PROMPT,
)
from app.sprint_memory.persistence.user_sprint_context_accessor import UserSprintContextAccessor
from app.sprint_memory.persistence.user_sprint_facts_accessor import UserSprintFactsAccessor
from app.sprint_memory.persistence.project_sprint_context_accessor import ProjectSprintContextAccessor
from app.sprint_memory.persistence.project_facts_accessor import ProjectFactsAccessor
from app.sprint_memory.persistence.sim_events_accessor import SimEventsAccessor
from app.utils.logger import logger


def _format_user_facts(facts: list) -> str:
    """Render a list of UserSprintFactItem into a readable text block."""
    if not facts:
        return "No structured facts available."
    lines = []
    for f in facts:
        lines.append(f"[{f.fact_type}] {f.summary}")
        if f.details:
            for k, v in list(f.details.items())[:3]:
                lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_project_facts(facts: list) -> str:
    """Render a list of ProjectFactItem into a readable text block."""
    if not facts:
        return "No project facts available."
    lines = []
    for f in facts:
        lines.append(f"[{f.project_name or f.project_id}][{f.fact_type}] {f.summary}")
    return "\n".join(lines)


class SummaryJobService:

    def __init__(self) -> None:
        self._user_context_accessor = UserSprintContextAccessor()
        self._user_facts_accessor = UserSprintFactsAccessor()
        self._project_context_accessor = ProjectSprintContextAccessor()
        self._project_facts_accessor = ProjectFactsAccessor()
        self._events_accessor = SimEventsAccessor()

    # ── Daily Summary ──────────────────────────────────────────────────────

    async def trigger_daily_summary(self, user_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Triggering daily summary job for user_id={user_id} job_id={job_id}")

        # Step 1 – fetch the most recent sprint context + recent facts from DynamoDB
        from boto3.dynamodb.conditions import Key
        from app.sprint_memory.constants import USER_PREFIX, SPRINT_PREFIX
        from app.sprint_memory.models.user_sprint_context import UserSprintContextItem

        pk = f"{USER_PREFIX}{user_id}"
        resp = self._user_context_accessor.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(SPRINT_PREFIX),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])

        activity_text: str
        sprint_id: Optional[str] = None

        if items:
            ctx = UserSprintContextItem(**items[0])
            sprint_id = ctx.sprint_id
            # Fetch recent facts for this sprint
            facts = self._user_facts_accessor.query_by_sprint(sprint_id=sprint_id, limit=20)
            user_facts = [f for f in facts if f.user_id == user_id]
            activity_text = _format_user_facts(user_facts)
        else:
            activity_text = "No activity data found in DynamoDB for this developer."

        # Step 2 – render prompt
        prompt = DAILY_SUMMARY_PROMPT.format(
            user_id=user_id,
            date=str(date.today()),
            activity=activity_text,
        )

        # Step 3 – call LLM
        try:
            summary = generate(prompt, max_tokens=512)
            status = "completed"
        except Exception as e:
            logger.error(f"LLM call failed for daily summary job_id={job_id}: {e}")
            summary = None
            status = "failed"

        # Step 4 – update UserSprintContext with the generated summary
        if summary and sprint_id and items:
            try:
                ctx = UserSprintContextItem(**items[0])
                ctx.summary.overall_status = summary[:500]
                ctx.last_refreshed_at = datetime.now(timezone.utc).isoformat()
                ctx.updated_at = ctx.last_refreshed_at
                self._user_context_accessor.put_context(ctx)
                logger.info(f"Stored daily summary in UserSprintContext for user_id={user_id}")
            except Exception as e:
                logger.warning(f"Failed to store daily summary in DynamoDB (non-fatal): {e}")

        return {
            "job_id": job_id,
            "status": status,
            "type": "daily_summary",
            "user_id": user_id,
            "sprint_id": sprint_id,
            "summary_preview": (summary[:200] + "...") if summary and len(summary) > 200 else summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Sprint Summary ─────────────────────────────────────────────────────

    async def trigger_sprint_summary(self, user_id: str, sprint_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Triggering sprint summary job for user_id={user_id} "
            f"sprint_id={sprint_id} job_id={job_id}"
        )

        # Step 1 – fetch all sprint facts for this user + sprint from DynamoDB
        try:
            facts = self._user_facts_accessor.query_by_sprint(sprint_id=sprint_id, limit=50)
            user_facts = [f for f in facts if f.user_id == user_id]
            activity_text = _format_user_facts(user_facts)
        except Exception as e:
            logger.warning(f"DynamoDB fetch failed for sprint summary (non-fatal): {e}")
            activity_text = "No activity data available — DynamoDB fetch failed."

        # Step 2 – render prompt
        prompt = SPRINT_SUMMARY_PROMPT.format(
            user_id=user_id,
            sprint_id=sprint_id,
            activity=activity_text,
        )

        # Step 3 – call LLM
        try:
            summary = generate(prompt, max_tokens=768)
            status = "completed"
        except Exception as e:
            logger.error(f"LLM call failed for sprint summary job_id={job_id}: {e}")
            summary = None
            status = "failed"

        # Step 4 – update UserSprintContext with the generated summary
        if summary:
            try:
                ctx = self._user_context_accessor.get_context(user_id, sprint_id)
                if ctx:
                    ctx.summary.overall_status = summary[:500]
                    ctx.last_refreshed_at = datetime.now(timezone.utc).isoformat()
                    ctx.updated_at = ctx.last_refreshed_at
                    self._user_context_accessor.put_context(ctx)
                    logger.info(f"Stored sprint summary in UserSprintContext for user_id={user_id} sprint_id={sprint_id}")
            except Exception as e:
                logger.warning(f"Failed to store sprint summary in DynamoDB (non-fatal): {e}")

        return {
            "job_id": job_id,
            "status": status,
            "type": "sprint_summary",
            "user_id": user_id,
            "sprint_id": sprint_id,
            "summary_preview": (summary[:200] + "...") if summary and len(summary) > 200 else summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Roadmap Summary ────────────────────────────────────────────────────

    async def trigger_roadmap_summary(self, sprint_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Triggering roadmap summary job for sprint_id={sprint_id} job_id={job_id}"
        )

        # Step 1 – fetch all project facts for this sprint from DynamoDB
        try:
            facts = self._project_facts_accessor.query_by_sprint(sprint_id=sprint_id, limit=100)
            project_text = _format_project_facts(facts)
        except Exception as e:
            logger.warning(f"DynamoDB fetch failed for roadmap summary (non-fatal): {e}")
            project_text = "No project data available — DynamoDB fetch failed."

        # Step 2 – render prompt
        prompt = ROADMAP_SUMMARY_PROMPT.format(
            sprint_id=sprint_id,
            project_data=project_text,
        )

        # Step 3 – call LLM
        try:
            summary = generate(prompt, max_tokens=768)
            status = "completed"
        except Exception as e:
            logger.error(f"LLM call failed for roadmap summary job_id={job_id}: {e}")
            summary = None
            status = "failed"

        # Step 4 – update all ProjectSprintContext records for this sprint
        if summary:
            try:
                from boto3.dynamodb.conditions import Key
                from app.sprint_memory.constants import SPRINT_PREFIX
                from app.sprint_memory.models.project_sprint_context import ProjectSprintContextItem

                gsi1pk = f"{SPRINT_PREFIX}{sprint_id}"
                resp = self._project_context_accessor.table.query(
                    IndexName="gsi1pk-gsi1sk-index",
                    KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
                    Limit=100,
                )
                now = datetime.now(timezone.utc).isoformat()
                for item in resp.get("Items", []):
                    try:
                        ctx = ProjectSprintContextItem(**item)
                        ctx.leadership_summary.one_liner = summary[:200]
                        ctx.last_refreshed_at = now
                        ctx.updated_at = now
                        self._project_context_accessor.put_context(ctx)
                    except Exception as inner_exc:
                        logger.warning(f"Failed to update project context item: {inner_exc}")
                logger.info(f"Stored roadmap summary in ProjectSprintContext for sprint_id={sprint_id}")
            except Exception as e:
                logger.warning(f"Failed to store roadmap summary in DynamoDB (non-fatal): {e}")

        return {
            "job_id": job_id,
            "status": status,
            "type": "roadmap_summary",
            "sprint_id": sprint_id,
            "summary_preview": (summary[:200] + "...") if summary and len(summary) > 200 else summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
