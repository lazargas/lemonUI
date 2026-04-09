from typing import Any, Dict

from pydantic import BaseModel, Field

from app.sprint_memory.constants import EVT_PREFIX, SIM_PREFIX, SPRINT_PREFIX, USER_PREFIX


class SimEventItem(BaseModel):
    pk: str = Field(description="USER#<userId>")
    sk: str = Field(description="EVT#<eventTime>#<simId>#<eventType>#<eventId>")

    entity_type: str = Field(default="sim_event")

    event_id: str
    source: str = Field(default="sim")

    user_id: str
    sprint_id: str

    sim_id: str
    sim_title: str = Field(default="")

    event_type: str
    event_time: str

    actor_user_id: str = Field(default="")
    actor_type: str = Field(default="")

    content: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    gsi1pk: str = Field(default="")
    gsi1sk: str = Field(default="")
    gsi2pk: str = Field(default="")
    gsi2sk: str = Field(default="")

    created_at: str

    @staticmethod
    def build_pk(user_id: str) -> str:
        return f"{USER_PREFIX}{user_id}"

    @staticmethod
    def build_sk(event_time: str, sim_id: str, event_type: str, discriminator: str) -> str:
        return f"{EVT_PREFIX}{event_time}#{sim_id}#{event_type}#{discriminator}"

    @staticmethod
    def build_gsi1pk(sim_id: str) -> str:
        return f"{SIM_PREFIX}{sim_id}"

    @staticmethod
    def build_gsi2pk(sprint_id: str) -> str:
        return f"{SPRINT_PREFIX}{sprint_id}"

    class Config:
        populate_by_name = True
