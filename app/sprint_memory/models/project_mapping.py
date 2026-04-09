from pydantic import BaseModel, Field

from app.sprint_memory.constants import PROJECT_PREFIX, SIM_PREFIX


class ProjectMappingItem(BaseModel):
    pk: str = Field(description="SIM#<simId>")
    sk: str = Field(description="PROJECT#<projectId>")

    entity_type: str = Field(default="project_mapping")

    sim_id: str
    project_id: str

    mapping_type: str = Field(default="explicit")
    mapping_source: str = Field(default="")
    mapping_confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    sim_title: str = Field(default="")
    project_name: str = Field(default="")

    gsi1pk: str = Field(default="")
    gsi1sk: str = Field(default="")

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(sim_id: str) -> str:
        return f"{SIM_PREFIX}{sim_id}"

    @staticmethod
    def build_sk(project_id: str) -> str:
        return f"{PROJECT_PREFIX}{project_id}"

    @staticmethod
    def build_gsi1pk(project_id: str) -> str:
        return f"{PROJECT_PREFIX}{project_id}"

    @staticmethod
    def build_gsi1sk(sim_id: str) -> str:
        return f"{SIM_PREFIX}{sim_id}"

    class Config:
        populate_by_name = True
