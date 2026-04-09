"""
Ingestion Endpoints
-------------------
POST /api/v1/ingestion/trigger          – trigger a data ingestion job
GET  /api/v1/ingestion/status/{jobId}   – check ingestion job status
"""
from fastapi import APIRouter, Path

from app.schemas.ingestion import IngestionStatusResponse, IngestionTriggerRequest
from app.services.ingestion_service import IngestionService

router = APIRouter()
_svc = IngestionService()


@router.post(
    "/trigger",
    response_model=IngestionStatusResponse,
    summary="Trigger a data ingestion job",
    description=(
        "Kicks off an ingestion job that fetches new or updated activity from "
        "the source system (Taskei) and stores it in the data layer. "
        "In production this enqueues an async job; the response returns immediately."
    ),
)
async def trigger_ingestion(body: IngestionTriggerRequest):
    return await _svc.trigger_ingestion(body)


@router.get(
    "/status/{jobId}",
    response_model=IngestionStatusResponse,
    summary="Get ingestion job status",
    description="Returns the current status and progress of an ingestion job.",
)
async def get_ingestion_status(
    jobId: str = Path(..., description="Ingestion job ID"),
):
    return await _svc.get_ingestion_status(job_id=jobId)
