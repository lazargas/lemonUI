from typing import List

from pydantic import BaseModel, Field

from app.sprint_memory.constants import PROJECT_METADATA_SK, PROJECT_PREFIX


class ProjectItem(BaseModel):
    pk: str = Field(description="PROJECT#<projectId>")
    sk: str = Field(default=PROJECT_METADATA_SK, description="Fixed value: METADATA")

    entity_type: str = Field(default="project")

    project_id: str
    project_name: str

    roadmap_item_id: str = Field(default="")
    roadmap_item_title: str = Field(default="")

    leadership_owner_user_id: str = Field(default="")
    engineering_owner_user_id: str = Field(default="")
    product_owner_user_id: str = Field(default="")

    description: str = Field(default="")

    status: str = Field(default="OPEN")
    priority: str = Field(default="MEDIUM")

    team: str = Field(default="")
    program: str = Field(default="")

    contributors: List[str] = Field(default_factory=list)

    created_at: str
    updated_at: str

    @staticmethod
    def build_pk(project_id: str) -> str:
        return f"{PROJECT_PREFIX}{project_id}"

    class Config:
        populate_by_name = True
