"""Small persistence adapter: SQLite for local demo, DynamoDB for SAM deployments."""
from __future__ import annotations

import json
import os
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from .config import AWS_REGION, DB_PATH

KEYS: dict[str, tuple[str, str | None]] = {
    "sites": ("site_id", None),
    "site_state": ("site_id", "state_key"),
    "alert_keys": ("idempotency_key", None),
    "issue_log": ("site_id", "issue_id"),
    "acks": ("alert_id", None),
    "rest_confirms": ("rest_key", None),
    "rulebooks": ("plan_id", "rule_id"),
    "obligation_log": ("site_id", "obligation_key"),
    "replay_runs": ("run_id", "event_id"),
}
ENV_TABLES = {
    "sites": "TABLE_SITES",
    "site_state": "TABLE_SITE_STATE",
    "alert_keys": "TABLE_ALERT_KEYS",
    "issue_log": "TABLE_ISSUE_LOG",
    "acks": "TABLE_ACKS",
    "rest_confirms": "TABLE_REST_CONFIRMS",
    "rulebooks": "TABLE_RULEBOOKS",
    "obligation_log": "TABLE_OBLIGATION_LOG",
    "replay_runs": "TABLE_REPLAY_RUNS",
}


def _ddb_safe(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _ddb_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_ddb_safe(item) for item in value]
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value) if value % 1 else int(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


class Store:
    def __init__(self) -> None:
        self.backend = os.getenv("STORAGE_BACKEND", "local").lower()
        self.db_path = Path(DB_PATH)
        self.ddb: Any = None
        if self.backend == "dynamodb":
            self.ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS records (entity TEXT NOT NULL, record_key TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(entity, record_key))")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path), timeout=10)

    def _table(self, entity: str):
        name = os.getenv(ENV_TABLES[entity], "")
        if not name:
            raise RuntimeError(f"DynamoDB table environment variable {ENV_TABLES[entity]} is required")
        return self.ddb.Table(name)

    def _key_string(self, entity: str, item: dict[str, Any]) -> str:
        pk, sk = KEYS[entity]
        return str(item[pk]) if sk is None else f"{item[pk]}|{item[sk]}"

    def get(self, entity: str, keys: dict[str, Any]) -> dict[str, Any] | None:
        if self.backend == "dynamodb":
            result = self._table(entity).get_item(Key=_ddb_safe(keys), ConsistentRead=True)
            return _plain(result.get("Item")) if result.get("Item") else None
        key = self._key_string(entity, keys)
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM records WHERE entity=? AND record_key=?", (entity, key)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, entity: str, item: dict[str, Any], *, append_only: bool = False) -> bool:
        pk, sk = KEYS[entity]
        key = self._key_string(entity, item)
        if self.backend == "dynamodb":
            kwargs: dict[str, Any] = {"Item": _ddb_safe(item)}
            if append_only:
                expression = f"attribute_not_exists({pk})"
                if sk:
                    expression += f" AND attribute_not_exists({sk})"
                kwargs["ConditionExpression"] = expression
            try:
                self._table(entity).put_item(**kwargs)
                return True
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                    return False
                raise
        with self._connect() as conn:
            if append_only:
                cursor = conn.execute("INSERT OR IGNORE INTO records(entity, record_key, payload) VALUES (?, ?, ?)", (entity, key, json.dumps(item, separators=(",", ":"))))
                return cursor.rowcount == 1
            conn.execute("INSERT INTO records(entity, record_key, payload) VALUES (?, ?, ?) ON CONFLICT(entity, record_key) DO UPDATE SET payload=excluded.payload", (entity, key, json.dumps(item, separators=(",", ":"))))
            return True

    def list(self, entity: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        if self.backend == "dynamodb":
            table = self._table(entity)
            scan_kwargs: dict[str, Any] = {}
            if filters:
                condition = None
                for name, value in filters.items():
                    part = Attr(name).eq(value)
                    condition = part if condition is None else condition & part
                scan_kwargs["FilterExpression"] = condition
            items: list[dict[str, Any]] = []
            while True:
                result = table.scan(**scan_kwargs)
                items.extend(_plain(result.get("Items", [])))
                if "LastEvaluatedKey" not in result:
                    return items
                scan_kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM records WHERE entity=?", (entity,)).fetchall()
        values = [json.loads(row[0]) for row in rows]
        return [item for item in values if all(item.get(key) == value for key, value in filters.items())]

    def increment(self, entity: str, key: dict[str, Any], increments: dict[str, int], set_values: dict[str, Any] | None = None) -> dict[str, Any]:
        set_values = set_values or {}
        if self.backend == "dynamodb":
            sets = [f"#{name}=:{name}" for name in set_values]
            adds = [f"#{name} :{name}" for name in increments]
            names = {f"#{name}": name for name in [*set_values, *increments]}
            values = {f":{name}": _ddb_safe(value) for name, value in {**set_values, **increments}.items()}
            expressions = []
            if sets:
                expressions.append("SET " + ", ".join(sets))
            if adds:
                expressions.append("ADD " + ", ".join(adds))
            response = self._table(entity).update_item(
                Key=_ddb_safe(key), UpdateExpression=" ".join(expressions),
                ExpressionAttributeNames=names, ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
            return _plain(response["Attributes"])
        record_key = self._key_string(entity, key)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT payload FROM records WHERE entity=? AND record_key=?", (entity, record_key)).fetchone()
            current = json.loads(row[0]) if row else dict(key)
            current.update(set_values)
            for name, amount in increments.items():
                current[name] = int(current.get(name, 0)) + amount
            conn.execute(
                "INSERT INTO records(entity, record_key, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(entity, record_key) DO UPDATE SET payload=excluded.payload",
                (entity, record_key, json.dumps(current, separators=(",", ":"))),
            )
            return current

    def delete(self, entity: str, key: dict[str, Any]) -> None:
        if self.backend == "dynamodb":
            self._table(entity).delete_item(Key=_ddb_safe(key))
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM records WHERE entity=? AND record_key=?", (entity, self._key_string(entity, key)))


store = Store()
