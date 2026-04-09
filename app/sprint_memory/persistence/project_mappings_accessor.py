from typing import List

from boto3.dynamodb.conditions import Key

from app.sprint_memory.constants import GSI1_NAME, PROJECT_MAPPINGS_TABLE, PROJECT_PREFIX
from app.sprint_memory.models.project_mapping import ProjectMappingItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class ProjectMappingsAccessor(BaseDynamoDBAccessor[ProjectMappingItem]):
    def __init__(self, table_name: str = PROJECT_MAPPINGS_TABLE):
        super().__init__(table_name=table_name, model=ProjectMappingItem)

    def put_mapping(self, item: ProjectMappingItem) -> ProjectMappingItem:
        return self.put_item(item)

    def get_projects_for_sim(self, sim_id: str) -> List[ProjectMappingItem]:
        pk = ProjectMappingItem.build_pk(sim_id)
        resp = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(PROJECT_PREFIX),
        )
        return [ProjectMappingItem(**item) for item in resp.get("Items", [])]

    def get_sims_for_project(self, project_id: str) -> List[ProjectMappingItem]:
        gsi1pk = ProjectMappingItem.build_gsi1pk(project_id)
        resp = self.table.query(
            IndexName=GSI1_NAME,
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
        )
        return [ProjectMappingItem(**item) for item in resp.get("Items", [])]
