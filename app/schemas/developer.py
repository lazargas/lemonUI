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

class StandupHelperResponse(BaseModel):
    user_id: str
    sprint_id: str
    suggested_talking_points: List[str] = []   # LLM-generated, max 3 items
    risks_to_mention: List[str] = []           # LLM-generated, max 3 items
    blockers: List[str] = []                   # LLM-generated, max 3 items
    pending_items: List[str] = []              # LLM-generated action items, max 3
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
