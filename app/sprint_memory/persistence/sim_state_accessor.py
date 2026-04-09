from typing import Optional

from app.sprint_memory.constants import SIM_STATE_SK, SIM_STATE_TABLE
from app.sprint_memory.models.sim_state import SimStateItem
from app.sprint_memory.persistence.base_ddb_accessor import BaseDynamoDBAccessor


class SimStateAccessor(BaseDynamoDBAccessor[SimStateItem]):
    def __init__(self, table_name: str = SIM_STATE_TABLE):
        super().__init__(table_name=table_name, model=SimStateItem)

    def get_state(self, sim_id: str) -> Optional[SimStateItem]:
        pk = SimStateItem.build_pk(sim_id)
        return self.get_item({"pk": pk, "sk": SIM_STATE_SK})

    def put_state(self, item: SimStateItem) -> SimStateItem:
        return self.put_item(item)
