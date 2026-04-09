from typing import List

from pydantic import BaseModel, Field

from app.sprint_memory.constants import PROJECT_PREFIX, SPRINT_PREFIX


class ProjectActiveUser(BaseModel):
    user_id: str
    role: str = Field(default="contributor")
    focus_area: str = Field(default="")


class ProjectActiveSim(BaseModel):
    sim_id: str
    title: str
    status: str
    owner_user_id: str
    last_updated_at: str = Field(default="")


class ProjectRisk(BaseModel):
    summary: str
    severity: str = Field(default="MEDIUM")


class ProjectDependency(BaseModel):
    summary: str


class ProjectSummary(BaseModel):
    overall_status: str = Field(default="")
    health: str = Field(default="GREEN")
    completion_confidence: str = Field(default="MEDIUM")


class LeadershipSummary(BaseModel):
    one_liner: str = Field(default="")
    what_changed: List[str] = Field(default_factory=list)
    needs_attention: List[str] = Field(default_factory=list)


class ProjectSprintMetrics(BaseModel):
    active_sim_count: int = Field(default=0)
    active_user_count: int = Field(default=0)
    active_risk_count: int = Field(default=0)
    active_blocker_count: int = Field(default=0)


class ProjectSprintContextItem(BaseModel):
    pk: str = Field(description="PROJECT#<projectId>")
    sk: str = Field(description="SPRINT#<sprintId>")

    entity_type: str = Field(default="project_sprint_context")

    project_id: str
    project_name: str = Field(default="")
    sprint_id: str

    last_refreshed_at: str

    summary: ProjectSummary = Field(default_factory=ProjectSummary)

    active_users: List[ProjectActiveUser] = Field(default_factory=list)
    active_sims: List[ProjectActiveSim] = Field(default_factory=list)

    recent_changes: List[str] = Field(default_factory=list)

    risks: List[ProjectRisk] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    dependencies: List[ProjectDependency] = Field(default_factory=list)

    leadership_summary: LeadershipSummary = Field(default_factory=LeadershipSummary)

    metrics: ProjectSprintMetrics = Field(default_factory=ProjectSprintMetrics)

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(project_id: str) -> str:
        return f"{PROJECT_PREFIX}{project_id}"

    @staticmethod
    def build_sk(sprint_id: str) -> str:
        return f"{SPRINT_PREFIX}{sprint_id}"

    class Config:
        populate_by_name = True
