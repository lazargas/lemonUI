from typing import List, Optional
from pydantic import BaseModel


class DailySummaryResponse(BaseModel):
    user_id: str
    date: str
    summary: str
    generated_at: str


class SprintSummaryResponse(BaseModel):
    user_id: str
    sprint_id: str
    summary: str
    generated_at: str


class SearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    sprint_id: Optional[str] = None
    limit: int = 5


class SearchResponse(BaseModel):
    query: str
    answer: str
    sources: list = []


# ── Standup Helper ────────────────────────────────────────────────────────────

class StandupItem(BaseModel):
    """A single standup bullet with an optional list of linked SIM/ticket URLs."""
    summary: str
    resources: List[str] = []   # e.g. ["https://issues.amazon.com/issues/TI-3137"]


class StandupHelperResponse(BaseModel):
    user_id: str
    sprint_id: str
    suggested_talking_points: List[StandupItem] = []
    risks_to_mention: List[StandupItem] = []
    blockers: List[StandupItem] = []
    pending_items: List[StandupItem] = []
    generated_at: str


# ── Pending Attention ─────────────────────────────────────────────────────────

class PendingAttentionItem(BaseModel):
    type: str
    sim_id: Optional[str] = None
    summary: str


class PendingAttentionResponse(BaseModel):
    user_id: str
    sprint_id: str
    items: List[PendingAttentionItem] = []
    generated_at: str


# ── Standup Cache (pre-generated bulk standup) ────────────────────────────────

class StandupTriggerRequest(BaseModel):
    aliases: List[str]
    sprint_id: str


class StandupTriggerResponse(BaseModel):
    job_id: str
    sprint_id: str
    aliases: List[str]
    started_at: str
    status: str = "started"


class CachedStandupResponse(BaseModel):
    user_id: str
    sprint_id: str
    suggested_talking_points: List[StandupItem] = []
    risks_to_mention: List[StandupItem] = []
    blockers: List[StandupItem] = []
    pending_items: List[StandupItem] = []
    generated_at: str
    job_id: str
    status: str  # "completed" | "failed" | "pending"
    error: Optional[str] = None
