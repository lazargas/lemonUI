from typing import Optional
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
