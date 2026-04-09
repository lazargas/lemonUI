from typing import List

from boto3.dynamodb.conditions import Attr, Key

from app.sprint_memory.constants import FACT_PREFIX, GSI1_NAME, GSI2_NAME, USER_SPRINT_FACTS_TABLE
from app.sprint_memory.models.user_sprint_fact import UserSprintFactItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class UserSprintFactsAccessor(BaseDynamoDBAccessor[UserSprintFactItem]):
    def __init__(self, table_name: str = USER_SPRINT_FACTS_TABLE):
        super().__init__(table_name=table_name, model=UserSprintFactItem)

    def put_fact(self, item: UserSprintFactItem) -> UserSprintFactItem:
        return self.put_item(item)

    def query_by_user(self, user_id: str, active_only: bool = False, limit: int = 100) -> List[UserSprintFactItem]:
        pk = UserSprintFactItem.build_pk(user_id)
        kwargs = dict(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(FACT_PREFIX),
            ScanIndexForward=False,
            Limit=limit,
        )
        if active_only:
            kwargs["FilterExpression"] = Attr("is_active").eq(True)
        resp = self.table.query(**kwargs)
        return [UserSprintFactItem(**item) for item in resp.get("Items", [])]

    def query_by_sprint(self, sprint_id: str, limit: int = 100) -> List[UserSprintFactItem]:
        gsi1pk = UserSprintFactItem.build_gsi1pk(sprint_id)
        resp = self.table.query(
            IndexName=GSI1_NAME,
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [UserSprintFactItem(**item) for item in resp.get("Items", [])]

    def query_by_sim(self, sim_id: str, limit: int = 100) -> List[UserSprintFactItem]:
        gsi2pk = UserSprintFactItem.build_gsi2pk(sim_id)
        resp = self.table.query(
            IndexName=GSI2_NAME,
            KeyConditionExpression=Key("gsi2pk").eq(gsi2pk),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [UserSprintFactItem(**item) for item in resp.get("Items", [])]

    def deactivate_fact(self, pk: str, sk: str, updated_at: str) -> bool:
        return self.update_item(
            key={"pk": pk, "sk": sk},
            update_expression="SET is_active = :val, updated_at = :ts",
            expression_values={":val": False, ":ts": updated_at},
        )
