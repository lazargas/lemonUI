from typing import List

from pydantic import BaseModel, Field

from app.sprint_memory.constants import SPRINT_PREFIX, USER_PREFIX


class ActiveSimSummary(BaseModel):
    sim_id: str
    title: str
    status: str
    priority: str
    recent_progress: List[str] = Field(default_factory=list)
    last_updated_at: str = Field(default="")


class PendingAttentionItem(BaseModel):
    type: str
    sim_id: str
    summary: str


class RiskItem(BaseModel):
    sim_id: str
    summary: str


class SprintSummary(BaseModel):
    primary_focus: List[str] = Field(default_factory=list)
    overall_status: str = Field(default="")


class SprintMetrics(BaseModel):
    active_sim_count: int = Field(default=0)
    active_blocker_count: int = Field(default=0)
    active_risk_count: int = Field(default=0)
    recent_fact_count: int = Field(default=0)


class UserSprintContextItem(BaseModel):
    pk: str = Field(description="USER#<userId>")
    sk: str = Field(description="SPRINT#<sprintId>")

    entity_type: str = Field(default="user_sprint_context")

    user_id: str
    sprint_id: str

    last_refreshed_at: str

    summary: SprintSummary = Field(default_factory=SprintSummary)
    active_sims: List[ActiveSimSummary] = Field(default_factory=list)
    recent_changes: List[str] = Field(default_factory=list)
    pending_attention: List[PendingAttentionItem] = Field(default_factory=list)
    suggested_talking_points: List[str] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    metrics: SprintMetrics = Field(default_factory=SprintMetrics)

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(user_id: str) -> str:
        return f"{USER_PREFIX}{user_id}"

    @staticmethod
    def build_sk(sprint_id: str) -> str:
        return f"{SPRINT_PREFIX}{sprint_id}"

    class Config:
        populate_by_name = True
