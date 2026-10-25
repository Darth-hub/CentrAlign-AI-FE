"""SQL persistence: PostgreSQL in deployment; SQLite for local tests."""
import json
from decimal import Decimal
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, Float
from config import settings
if settings.database_url.startswith("sqlite:///./"):
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {})
metadata = MetaData()
records = Table("records", metadata,
    Column("collection", String(100), primary_key=True), Column("key", String(600), primary_key=True),
    Column("body", Text, nullable=False))
jobs = Table("jobs", metadata,
    Column("id", String(40), primary_key=True), Column("owner", String(320), nullable=False),
    Column("kind", String(40), nullable=False), Column("payload", Text, nullable=False),
    Column("status", String(40), nullable=False), Column("active_key", String(600), unique=True),
    Column("created", Float, nullable=False), Column("heartbeat", Float, nullable=False))
events = Table("job_events", metadata,
    Column("sequence", Integer, primary_key=True, autoincrement=True),
    Column("job_id", String(40), nullable=False, index=True), Column("body", Text, nullable=False))
def initialize(): metadata.create_all(engine)
def encode(value):
    return json.dumps(value, default=lambda x: float(x) if isinstance(x, Decimal) else str(x), allow_nan=False)
