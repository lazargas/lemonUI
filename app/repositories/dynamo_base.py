from typing import Any, Dict, Generic, List, Optional, TypeVar
from boto3.dynamodb.conditions import Key, Attr
from app.db.dynamo import get_table

T = TypeVar("T")


class DynamoBaseRepository(Generic[T]):
    """
    Generic DynamoDB repository.

    Subclasses must set:
        table_name  – DynamoDB table name
        pk_name     – partition key attribute name  (default: "pk")
        sk_name     – sort key attribute name       (default: None, single-key table)
    """

    table_name: str = ""
    pk_name: str = "pk"
    sk_name: Optional[str] = None

    def __init__(self):
        self._table = get_table(self.table_name)

    # ── helpers ────────────────────────────────────────────────────────────

    def _key(self, pk: str, sk: Optional[str] = None) -> Dict[str, Any]:
        key: Dict[str, Any] = {self.pk_name: pk}
        if self.sk_name and sk is not None:
            key[self.sk_name] = sk
        return key

    # ── CRUD ───────────────────────────────────────────────────────────────

    def get(self, pk: str, sk: Optional[str] = None) -> Optional[Dict[str, Any]]:
        response = self._table.get_item(Key=self._key(pk, sk))
        return response.get("Item")

    def put(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self._table.put_item(Item=item)
        return item

    def delete(self, pk: str, sk: Optional[str] = None) -> None:
        self._table.delete_item(Key=self._key(pk, sk))

    def update(
        self,
        pk: str,
        updates: Dict[str, Any],
        sk: Optional[str] = None,
    ) -> Dict[str, Any]:
        update_expr = "SET " + ", ".join(f"#k{i} = :v{i}" for i in range(len(updates)))
        expr_names = {f"#k{i}": k for i, k in enumerate(updates.keys())}
        expr_values = {f":v{i}": v for i, v in enumerate(updates.values())}

        response = self._table.update_item(
            Key=self._key(pk, sk),
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes", {})

    def query(
        self,
        pk: str,
        sk_begins_with: Optional[str] = None,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": Key(self.pk_name).eq(pk),
            "Limit": limit,
        }
        if sk_begins_with and self.sk_name:
            kwargs["KeyConditionExpression"] &= Key(self.sk_name).begins_with(
                sk_begins_with
            )
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = self._table.query(**kwargs)
        return {
            "items": response.get("Items", []),
            "last_evaluated_key": response.get("LastEvaluatedKey"),
            "count": response.get("Count", 0),
        }

    def scan(
        self,
        filter_expression=None,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"Limit": limit}
        if filter_expression is not None:
            kwargs["FilterExpression"] = filter_expression
        if last_evaluated_key:
            kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = self._table.scan(**kwargs)
        return {
            "items": response.get("Items", []),
            "last_evaluated_key": response.get("LastEvaluatedKey"),
            "count": response.get("Count", 0),
        }
