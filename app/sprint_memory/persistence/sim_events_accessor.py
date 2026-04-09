from typing import List

from boto3.dynamodb.conditions import Key

from app.sprint_memory.constants import EVT_PREFIX, GSI1_NAME, GSI2_NAME, SIM_EVENTS_TABLE
from app.sprint_memory.models.sim_event import SimEventItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class SimEventsAccessor(BaseDynamoDBAccessor[SimEventItem]):
    def __init__(self, table_name: str = SIM_EVENTS_TABLE):
        super().__init__(table_name=table_name, model=SimEventItem)

    def put_event(self, item: SimEventItem) -> SimEventItem:
        return self.put_item(item)

    def query_by_user(self, user_id: str, limit: int = 100) -> List[SimEventItem]:
        pk = SimEventItem.build_pk(user_id)
        resp = self.table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(EVT_PREFIX),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [SimEventItem(**item) for item in resp.get("Items", [])]

    def query_by_sim(self, sim_id: str, limit: int = 100) -> List[SimEventItem]:
        gsi1pk = SimEventItem.build_gsi1pk(sim_id)
        resp = self.table.query(
            IndexName=GSI1_NAME,
            KeyConditionExpression=Key("gsi1pk").eq(gsi1pk),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [SimEventItem(**item) for item in resp.get("Items", [])]

    def query_by_sprint(self, sprint_id: str, limit: int = 100) -> List[SimEventItem]:
        gsi2pk = SimEventItem.build_gsi2pk(sprint_id)
        resp = self.table.query(
            IndexName=GSI2_NAME,
            KeyConditionExpression=Key("gsi2pk").eq(gsi2pk),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [SimEventItem(**item) for item in resp.get("Items", [])]
