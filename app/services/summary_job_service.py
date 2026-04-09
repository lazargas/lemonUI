"""
Summary Job Service
-------------------
Handles on-demand triggering of summary generation jobs
(daily summary, sprint summary, roadmap summary).

In production these run on a schedule (EventBridge / cron).
This service allows manual triggering via API for dev/testing.

NOTE: LLM calls and DynamoDB writes are stubbed with TODO markers.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.llm.llm_service import generate
from app.llm.prompts import (
    DAILY_SUMMARY_PROMPT,
    SPRINT_SUMMARY_PROMPT,
    ROADMAP_SUMMARY_PROMPT,
)
from app.utils.logger import logger


class SummaryJobService:

    async def trigger_daily_summary(self, user_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Triggering daily summary job for user_id={user_id} job_id={job_id}")

        # TODO: Step 1 – fetch yesterday's activity from DynamoDB
        # activity_records = await activity_repo.get_yesterday(user_id)
        # activity_text = format_activity(activity_records)
        activity_text = "No activity data yet — wire in DynamoDB repository."

        # Step 2 – render prompt
        from datetime import date
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

        # TODO: Step 4 – store result in DynamoDB daily_summaries table
        # await daily_summary_repo.put({
        #     "user_id": user_id,
        #     "date": str(date.today()),
        #     "summary": summary,
        #     "generated_at": datetime.now(timezone.utc).isoformat(),
        # })

        return {
            "job_id": job_id,
            "status": status,
            "type": "daily_summary",
            "user_id": user_id,
            "summary_preview": (summary[:200] + "...") if summary and len(summary) > 200 else summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def trigger_sprint_summary(self, user_id: str, sprint_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Triggering sprint summary job for user_id={user_id} "
            f"sprint_id={sprint_id} job_id={job_id}"
        )

        # TODO: Step 1 – fetch all sprint activity from DynamoDB
        # activity_records = await activity_repo.get_by_sprint(user_id, sprint_id)
        # activity_text = format_activity(activity_records)
        activity_text = "No activity data yet — wire in DynamoDB repository."

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

        # TODO: Step 4 – store result in DynamoDB sprint_summaries table
        # await sprint_summary_repo.put({...})

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

    async def trigger_roadmap_summary(self, sprint_id: str) -> dict:
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Triggering roadmap summary job for sprint_id={sprint_id} job_id={job_id}"
        )

        # TODO: Step 1 – fetch project facts and sprint context from DynamoDB
        # project_data = await project_facts_repo.get_all_for_sprint(sprint_id)
        # project_text = format_project_data(project_data)
        project_text = "No project data yet — wire in DynamoDB repository."

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

        # TODO: Step 4 – store result in DynamoDB roadmap_summaries table
        # await roadmap_summary_repo.put({...})

        return {
            "job_id": job_id,
            "status": status,
            "type": "roadmap_summary",
            "sprint_id": sprint_id,
            "summary_preview": (summary[:200] + "...") if summary and len(summary) > 200 else summary,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
