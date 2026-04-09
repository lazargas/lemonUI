from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.sprint_memory.constants import FACT_PREFIX, SIM_PREFIX, SPRINT_PREFIX, USER_PREFIX


class UserSprintFactItem(BaseModel):
    pk: str = Field(description="USER#<userId>")
    sk: str = Field(description="FACT#<factTime>#<factId>")

    entity_type: str = Field(default="sprint_fact")

    fact_id: str
    user_id: str
    sprint_id: str

    sim_id: str
    sim_title: str = Field(default="")

    fact_type: str
    fact_time: str

    summary: str

    details: Dict[str, Any] = Field(default_factory=dict)
    evidence_event_ids: List[str] = Field(default_factory=list)

    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0)

    is_active: bool = Field(default=True)

    gsi1pk: str = Field(default="")
    gsi1sk: str = Field(default="")
    gsi2pk: str = Field(default="")
    gsi2sk: str = Field(default="")

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(user_id: str) -> str:
        return f"{USER_PREFIX}{user_id}"

    @staticmethod
    def build_sk(fact_time: str, fact_id: str) -> str:
        return f"{FACT_PREFIX}{fact_time}#{fact_id}"

    @staticmethod
    def build_gsi1pk(sprint_id: str) -> str:
        return f"{SPRINT_PREFIX}{sprint_id}"

    @staticmethod
    def build_gsi2pk(sim_id: str) -> str:
        return f"{SIM_PREFIX}{sim_id}"

    class Config:
        populate_by_name = True
