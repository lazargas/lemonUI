from typing import List, Optional
from pydantic import BaseModel


class SprintContextResponse(BaseModel):
    project_id: str
    sprint_id: str
    context_summary: str
    generated_at: str


class ProjectFact(BaseModel):
    fact_id: str
    project_id: str
    sprint_id: str
    category: str          # e.g. "blocker", "risk", "dependency", "decision"
    content: str
    recorded_at: str


class ProjectFactsResponse(BaseModel):
    project_id: str
    sprint_id: str
    facts: List[ProjectFact]


class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    sprint_id: str
    health: str            # e.g. "green", "yellow", "red"
    summary: str


class ProjectsListResponse(BaseModel):
    sprint_id: str
    projects: List[ProjectSummary]


class TimelineEvent(BaseModel):
    event_id: str
    project_id: str
    sprint_id: str
    event_type: str        # e.g. "status_change", "blocker_added", "decision_made"
    description: str
    occurred_at: str


class TimelineResponse(BaseModel):
    project_id: str
    sprint_id: str
    events: List[TimelineEvent]


class RoadmapSummaryResponse(BaseModel):
    sprint_id: str
    summary: str
    risks: List[str]
    dependencies: List[str]
    health_overview: str
    generated_at: str
