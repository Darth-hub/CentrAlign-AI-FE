"""Persistent queue. Uncertain interrupted writes require reconciliation, never blind replay."""
import json
import time
import uuid
from sqlalchemy import select, update, insert
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from services.database import engine, jobs, events, encode

def enqueue(kind, payload, claims, document_id):
    now = time.time()
    job_id = str(uuid.uuid4())
    # Store only verified identity fields, never bearer tokens/API keys.
    identity = {k: claims.get(k, "") for k in ("sub", "email", "p2p_role", "department")}
    try:
        with engine.begin() as conn:
            conn.execute(insert(jobs).values(id=job_id, owner=claims["email"], kind=kind,
                payload=encode({"input": payload, "identity": identity}), status="queued",
                active_key=document_id, created=now, heartbeat=now))
    except IntegrityError as exc:
        raise HTTPException(409, "This document already has an active or unreconciled job") from exc
    return job_id

def get_job(job_id, claims=None):
    with engine.connect() as conn:
        row = conn.execute(select(jobs).where(jobs.c.id == job_id)).mappings().first()
    if not row: raise HTTPException(404, "Job not found")
    if claims and claims["email"] != row["owner"] and claims["p2p_role"] != "admin":
        raise HTTPException(403, "Job belongs to another user")
    return dict(row)

def append_event(job_id, event):
    with engine.begin() as conn:
        conn.execute(insert(events).values(job_id=job_id, body=encode(event)))

def poll(job_id, after, claims):
    job = get_job(job_id, claims)
    with engine.connect() as conn:
        rows = conn.execute(select(events).where(events.c.job_id == job_id,
            events.c.sequence > after).order_by(events.c.sequence).limit(100)).mappings().all()
    return {"status": job["status"], "events": [{"sequence": r["sequence"], **json.loads(r["body"])} for r in rows]}

def set_status(job_id, status):
    values = {"status": status, "heartbeat": time.time()}
    if status in {"completed", "failed", "reconciled"}: values["active_key"] = None
    with engine.begin() as conn:
        conn.execute(update(jobs).where(jobs.c.id == job_id).values(**values))

def heartbeat(job_id):
    with engine.begin() as conn:
        conn.execute(update(jobs).where(jobs.c.id == job_id).values(heartbeat=time.time()))

def claim():
    # Compare-and-set also works in local SQLite; only one worker wins a row.
    with engine.begin() as conn:
        row = conn.execute(select(jobs).where(jobs.c.status == "queued").order_by(jobs.c.created).limit(1)).mappings().first()
        if not row: return None
        changed = conn.execute(update(jobs).where(jobs.c.id == row["id"], jobs.c.status == "queued")
            .values(status="running", heartbeat=time.time())).rowcount
        return dict(row) if changed == 1 else None

def interrupt_stale():
    with engine.connect() as conn:
        ids = list(conn.execute(select(jobs.c.id).where(jobs.c.status == "running",
            jobs.c.heartbeat < time.time() - 60)).scalars())
    for job_id in ids:
        # Compare heartbeat again in the write so a renewed lease is not interrupted.
        with engine.begin() as conn:
            changed = conn.execute(update(jobs).where(jobs.c.id == job_id,
                jobs.c.status == "running", jobs.c.heartbeat < time.time() - 60)
                .values(status="interrupted", heartbeat=time.time())).rowcount
        if changed:
            append_event(job_id, {"type": "error", "error": "Worker interrupted; reconcile ERP state before retrying"})
