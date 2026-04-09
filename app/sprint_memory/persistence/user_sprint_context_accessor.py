from typing import Optional

from app.sprint_memory.constants import USER_SPRINT_CONTEXT_TABLE
from app.sprint_memory.models.user_sprint_context import UserSprintContextItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class UserSprintContextAccessor(BaseDynamoDBAccessor[UserSprintContextItem]):
    def __init__(self, table_name: str = USER_SPRINT_CONTEXT_TABLE):
        super().__init__(table_name=table_name, model=UserSprintContextItem)

    def get_context(self, user_id: str, sprint_id: str) -> Optional[UserSprintContextItem]:
        pk = UserSprintContextItem.build_pk(user_id)
        sk = UserSprintContextItem.build_sk(sprint_id)
        return self.get_item({"pk": pk, "sk": sk})

    def put_context(self, item: UserSprintContextItem) -> UserSprintContextItem:
        return self.put_item(item)
