from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.sprint_memory.constants import FACT_PREFIX, PROJECT_PREFIX, SPRINT_PREFIX


class ProjectFactItem(BaseModel):
    pk: str = Field(description="PROJECT#<projectId>")
    sk: str = Field(description="FACT#<factTime>#<factId>")

    entity_type: str = Field(default="project_fact")

    fact_id: str
    project_id: str
    project_name: str = Field(default="")

    sprint_id: str

    fact_type: str
    fact_time: str

    summary: str

    details: Dict[str, Any] = Field(default_factory=dict)

    source_sim_ids: List[str] = Field(default_factory=list)
    source_user_ids: List[str] = Field(default_factory=list)
    evidence_event_ids: List[str] = Field(default_factory=list)

    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)

    is_active: bool = Field(default=True)

    gsi1pk: str = Field(default="")
    gsi1sk: str = Field(default="")

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(project_id: str) -> str:
        return f"{PROJECT_PREFIX}{project_id}"

    @staticmethod
    def build_sk(fact_time: str, fact_id: str) -> str:
        return f"{FACT_PREFIX}{fact_time}#{fact_id}"

    @staticmethod
    def build_gsi1pk(sprint_id: str) -> str:
        return f"{SPRINT_PREFIX}{sprint_id}"

    class Config:
        populate_by_name = True
