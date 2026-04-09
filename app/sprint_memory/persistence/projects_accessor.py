from typing import Optional

from app.sprint_memory.constants import PROJECT_METADATA_SK, PROJECTS_TABLE
from app.sprint_memory.models.project import ProjectItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class ProjectsAccessor(BaseDynamoDBAccessor[ProjectItem]):
    def __init__(self, table_name: str = PROJECTS_TABLE):
        super().__init__(table_name=table_name, model=ProjectItem)

    def get_project(self, project_id: str) -> Optional[ProjectItem]:
        pk = ProjectItem.build_pk(project_id)
        return self.get_item({"pk": pk, "sk": PROJECT_METADATA_SK})

    def put_project(self, item: ProjectItem) -> ProjectItem:
        return self.put_item(item)
