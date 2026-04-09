from typing import List

from boto3.dynamodb.conditions import Attr, Key

from app.sprint_memory.constants import FACT_PREFIX, GSI1_NAME, PROJECT_FACTS_TABLE
from app.sprint_memory.models.project_fact import ProjectFactItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class ProjectFactsAccessor(BaseDynamoDBAccessor[ProjectFactItem]):
    def __init__(self, table_name: str = PROJECT_FACTS_TABLE):
        super().__init__(table_name=table_name, model=ProjectFactItem)

    def put_fact(self, item: ProjectFactItem) -> ProjectFactItem:
        return self.put_item(item)

    def query_by_project(self, project_id: str, active_only: bool = False, limit: int = 100) -> List[ProjectFactItem]:
        pk = ProjectFactItem.build_pk(project_id)
        kwargs = dict(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(FACT_PREFIX),
            ScanIndexForward=False,
            Limit=limit,
        )
        if active_only:
            kwargs["FilterExpression"] = Attr("is_active").eq(True)
        resp = self.table.query(**kwargs)
        return [ProjectFactItem(**item) for item in resp.get("Items", [])]

    def query_by_sprint(self, sprint_id: str, limit: int = 100) -> List[ProjectFactItem]:
        gsi1pk = ProjectFactItem.build_gsi1pk(sprint_id)
        resp = self.table.query(
            IndexName=GSI1_NAME,
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [ProjectFactItem(**item) for item in resp.get("Items", [])]

    def deactivate_fact(self, pk: str, sk: str, updated_at: str) -> bool:
        return self.update_item(
            key={"pk": pk, "sk": sk},
            update_expression="SET is_active = :val, updated_at = :ts",
            expression_values={":val": False, ":ts": updated_at},
        )
