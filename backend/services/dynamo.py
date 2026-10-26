"""Legacy import name for the SQL repository; no DynamoDB calls."""
import json
from sqlalchemy import select, delete, update
from services.database import engine, records, encode
KEYS = {"supplier-quotes": "quote_id", "approval-snapshots": "document_id", "document-lifecycle": "document_id", "invoice-jobs": "job_id", "chat-sessions": "user_id",
        "chat-messages": "message_id", "errors": "error_id", "agent-errors": "error_id", "contracts": "agreement_id"}
def _key(collection, item):
    field = KEYS.get(collection)
    if not field or field not in item: raise ValueError(f"Missing primary key for {collection}")
    return str(item[field])
def put_item(table_name, item):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
    stmt = insert(records).values(collection=table_name, key=_key(table_name, item), body=encode(item))
    with engine.begin() as conn:
        conn.execute(stmt.on_conflict_do_update(index_elements=["collection", "key"], set_={"body": stmt.excluded.body}))
    return item
def get_item(table_name, key):
    with engine.connect() as conn:
        body = conn.execute(select(records.c.body).where(records.c.collection == table_name,
            records.c.key == _key(table_name, key))).scalar_one_or_none()
    return json.loads(body) if body else None
def update_item(table_name, key, updates):
    with engine.begin() as conn:
        query = select(records.c.body).where(records.c.collection == table_name,
            records.c.key == _key(table_name, key)).with_for_update()
        body = conn.execute(query).scalar_one_or_none()
        if body is None: raise KeyError(key)
        item = json.loads(body)
        item.update(updates)
        conn.execute(update(records).where(records.c.collection == table_name,
            records.c.key == _key(table_name, key)).values(body=encode(item)))
    return item
def scan_table(table_name, filter_expr=None, expr_values=None):
    if filter_expr is not None: raise ValueError("DynamoDB filter expressions are no longer supported")
    with engine.connect() as conn:
        return [json.loads(x) for x in conn.execute(select(records.c.body).where(records.c.collection == table_name)).scalars()]
def delete_item(table_name, key):
    with engine.begin() as conn:
        conn.execute(delete(records).where(records.c.collection == table_name, records.c.key == _key(table_name, key)))
def clear_table(table_name):
    with engine.begin() as conn:
        return conn.execute(delete(records).where(records.c.collection == table_name)).rowcount
class SQLTable:
    def __init__(self, name): self.name = name
    def put_item(self, Item): return put_item(self.name, Item)
    def get_item(self, Key, **kwargs): return {"Item": get_item(self.name, Key)}
    def delete_item(self, Key): return delete_item(self.name, Key)
    def scan(self, **kwargs): return {"Items": scan_table(self.name)}
    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues, **kwargs):
        values = {ExpressionAttributeNames[k.strip()]: ExpressionAttributeValues[v.strip()]
                  for k, v in (part.split("=", 1) for part in UpdateExpression.removeprefix("SET ").split(","))}
        return {"Attributes": update_item(self.name, Key, values)}
def get_table(name): return SQLTable(name)
