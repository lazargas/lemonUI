from typing import Optional

from app.sprint_memory.constants import PROJECT_SPRINT_CONTEXT_TABLE
from app.sprint_memory.models.project_sprint_context import ProjectSprintContextItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class ProjectSprintContextAccessor(BaseDynamoDBAccessor[ProjectSprintContextItem]):
    def __init__(self, table_name: str = PROJECT_SPRINT_CONTEXT_TABLE):
        super().__init__(table_name=table_name, model=ProjectSprintContextItem)

    def get_context(self, project_id: str, sprint_id: str) -> Optional[ProjectSprintContextItem]:
        pk = ProjectSprintContextItem.build_pk(project_id)
        sk = ProjectSprintContextItem.build_sk(sprint_id)
        return self.get_item({"pk": pk, "sk": sk})

    def put_context(self, item: ProjectSprintContextItem) -> ProjectSprintContextItem:
        return self.put_item(item)
