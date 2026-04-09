"""
Ingestion Service
-----------------
Handles triggering and status-checking of data ingestion jobs.

NOTE: Actual ingestion logic (Taskei API calls, DynamoDB writes,
      embedding generation) is stubbed with TODO markers.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.schemas.ingestion import IngestionStatusResponse, IngestionTriggerRequest
from app.utils.logger import logger


class IngestionService:

    async def trigger_ingestion(
        self, request: IngestionTriggerRequest
    ) -> IngestionStatusResponse:
        """
        Kick off an ingestion job for the given source / developer / sprint.

        In production this should enqueue an SQS message or trigger a
        Step Functions execution rather than running synchronously.
        """
        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Ingestion triggered job_id={job_id} source={request.source} "
            f"user_id={request.user_id} sprint_id={request.sprint_id}"
        )

        # TODO: enqueue SQS message / trigger Step Functions
        # await sqs_client.send_message(
        #     QueueUrl=settings.INGESTION_QUEUE_URL,
        #     MessageBody=json.dumps({
        #         "job_id": job_id,
        #         "source": request.source,
        #         "user_id": request.user_id,
        #         "sprint_id": request.sprint_id,
        #     }),
        # )

        return IngestionStatusResponse(
            job_id=job_id,
            status="queued",
            source=request.source,
            records_processed=0,
            started_at=started_at,
        )

    async def get_ingestion_status(self, job_id: str) -> IngestionStatusResponse:
        """
        Return the current status of an ingestion job.
        """
        logger.info(f"Fetching ingestion status for job_id={job_id}")

        # TODO: fetch from DynamoDB jobs table
        # record = await ingestion_job_repo.get(job_id)

        return IngestionStatusResponse(
            job_id=job_id,
            status="unknown",
            source="taskei",
            records_processed=0,
            error="Job tracking not yet connected to the data layer.",
        )
