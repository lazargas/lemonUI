from typing import Optional
from pydantic import BaseModel


class IngestionTriggerRequest(BaseModel):
    source: str = "taskei"
    user_id: Optional[str] = None      # None = ingest all developers
    sprint_id: Optional[str] = None    # None = current sprint


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: str                        # "queued" | "running" | "completed" | "failed"
    source: str
    records_processed: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
