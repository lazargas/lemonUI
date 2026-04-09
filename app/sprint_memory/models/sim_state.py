from typing import List, Optional

from pydantic import BaseModel, Field

from app.sprint_memory.constants import SIM_PREFIX, SIM_STATE_SK


class SimStateItem(BaseModel):
    pk: str = Field(description="SIM#<simId>")
    sk: str = Field(default=SIM_STATE_SK, description="Fixed value: STATE")

    entity_type: str = Field(default="sim_state")

    sim_id: str
    sprint_id: str

    title: str
    description: str = Field(default="")
    description_hash: str = Field(default="", description="sha256 hash for cheap diff detection")

    status: str
    priority: str

    owner_user_id: str
    reporter_user_id: str = Field(default="")

    labels: List[str] = Field(default_factory=list)
    team: str = Field(default="")

    known_comment_ids: List[str] = Field(default_factory=list)
    latest_comment_at: Optional[str] = Field(default=None)
    latest_sim_updated_at: Optional[str] = Field(default=None)

    raw_snapshot_s3_key: str = Field(default="")

    created_at: str
    last_seen_at: str

    version: int = Field(default=1)

    @staticmethod
    def build_pk(sim_id: str) -> str:
        return f"{SIM_PREFIX}{sim_id}"

    class Config:
        populate_by_name = True
