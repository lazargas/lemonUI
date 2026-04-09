from decimal import Decimal
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from app.db.dynamo import get_dynamodb_resource
from app.utils.logger import logger


def _floats_to_decimals(obj: Any) -> Any:
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimals(v) for v in obj]
    return obj


T = TypeVar("T", bound=BaseModel)


class BaseDynamoDBAccessor(Generic[T]):
    def __init__(self, table_name: str, model: Type[T]):
        self.dynamodb = get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)
        self.model = model
        self.logger = logger

    def put_item(self, item: T) -> T:
        try:
            self.table.put_item(Item=_floats_to_decimals(item.model_dump()))
            return item
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error putting item in table {self.table.name}", exc_info=e)
            raise

    def get_item(self, key: dict) -> Optional[T]:
        try:
            response = self.table.get_item(Key=key)
            item: dict = response.get("Item", {})
            return self.model(**item) if item else None
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error getting item with key {key} from table {self.table.name}", exc_info=e)
            raise

    def update_item(self, key: dict, update_expression: str, expression_values: dict) -> bool:
        try:
            self.table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
            )
            return True
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error updating item with key {key} in table {self.table.name}", exc_info=e)
            raise

    def delete_item(self, key: dict) -> bool:
        try:
            self.table.delete_item(Key=key)
            return True
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error deleting item with key {key} from table {self.table.name}", exc_info=e)
            raise

    def batch_get_items(self, keys: List[dict]) -> List[T]:
        batch_size = 100
        results: List[T] = []

        try:
            for i in range(0, len(keys), batch_size):
                batch_keys = keys[i : i + batch_size]
                request_items: Dict[str, Any] = {self.table.name: {"Keys": batch_keys}}

                response = self.dynamodb.batch_get_item(RequestItems=request_items)
                if "Responses" in response and self.table.name in response["Responses"]:
                    results.extend([self.model(**item) for item in response["Responses"][self.table.name]])

                if "UnprocessedKeys" in response and self.table.name in response["UnprocessedKeys"]:
                    unprocessed = response["UnprocessedKeys"][self.table.name]["Keys"]
                    self.logger.warning(f"Unprocessed keys in table {self.table.name}: {unprocessed}")
                    raise ValueError(f"Unprocessed keys in table {self.table.name}: {unprocessed}")

            return results

        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error batch getting items from table {self.table.name}", exc_info=e)
            raise
