# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""SQL-backed chat session and message persistence, scoped to the verified user."""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel

from services.dynamo import get_item, put_item, get_table

router = APIRouter()
logger = logging.getLogger("p2p.chat")

SESSION_TABLE = "chat-sessions"


class ChatMessageIn(BaseModel):
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    tools_used: list[str] = []


class ChatSessionCreate(BaseModel):
    session_id: str
    title: str


# ── Actor ID helper ─────────────────────────────────────────────────────────
# AgentCore actorId: [a-zA-Z0-9][a-zA-Z0-9-_/]*


def _email_to_actor(email):
    return email  # Lossless tenant key; punctuation replacement can collide.

def _resolve_email(authorization):
    from services.auth import claims_from_header
    return claims_from_header(authorization)["email"]


# ── Session index (DynamoDB) ────────────────────────────────────────────────


def _get_sessions(email: str) -> list[dict]:
    item = get_item(SESSION_TABLE, {"user_id": email})
    if not item:
        return []
    return item.get("sessions", [])


def _save_sessions(email: str, sessions: list[dict]):
    put_item(SESSION_TABLE, {
        "user_id": email,
        "sessions": sessions[:30],
        "updated_at": datetime.utcnow().isoformat(),
    })


def update_session_title(email: str, session_id: str, new_title: str):
    """Update the title of a specific session in the DDB session index."""
    sessions = _get_sessions(email)
    for s in sessions:
        if s["id"] == session_id:
            s["title"] = new_title
            break
    _save_sessions(email, sessions)


def generate_title(messages):
    return next((m.get("content", "")[:60] for m in messages if m.get("role") == "user"), "")

def _store_message(actor_id, session_id, role, content):
    import uuid
    put_item("chat-messages", {"message_id": str(uuid.uuid4()), "actor_id": actor_id,
        "session_id": session_id, "role": role, "content": content,
        "timestamp": datetime.utcnow().isoformat(), "tools_used": []})

def _load_messages(actor_id, session_id):
    from services.dynamo import scan_table
    rows = [r for r in scan_table("chat-messages") if r["actor_id"] == actor_id and r["session_id"] == session_id]
    return sorted(rows, key=lambda r: r["timestamp"])

def _delete_session_events(actor_id, session_id):
    from services.dynamo import delete_item
    for row in _load_messages(actor_id, session_id):
        delete_item("chat-messages", {"message_id": row["message_id"]})


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get("/sessions")
def list_sessions(authorization: Optional[str] = Header(None)):
    """List chat sessions for the current user."""
    email = _resolve_email(authorization)
    sessions = _get_sessions(email)
    return {"sessions": sessions, "user": email}


@router.post("/sessions")
def create_session(data: ChatSessionCreate, authorization: Optional[str] = Header(None)):
    """Create a new chat session."""
    email = _resolve_email(authorization)
    sessions = _get_sessions(email)

    new_session = {
        "id": data.session_id,
        "title": data.title,
        "created_at": datetime.utcnow().isoformat(),
    }

    sessions = [new_session] + [s for s in sessions if s["id"] != data.session_id]
    _save_sessions(email, sessions)

    return new_session


@router.get("/sessions/{session_id}")
def get_session_messages(session_id: str, authorization: Optional[str] = Header(None)):
    """Get all messages for a chat session from AgentCore Memory."""
    email = _resolve_email(authorization)
    actor_id = _email_to_actor(email)
    messages = _load_messages(actor_id, session_id)
    return {"session_id": session_id, "messages": messages}


@router.post("/message")
def save_message(data: ChatMessageIn, authorization: Optional[str] = Header(None)):
    """Save a chat message to AgentCore Memory. DDB is not updated — it's just a session pointer."""
    email = _resolve_email(authorization)
    actor_id = _email_to_actor(email)

    # Store in AgentCore Memory (the only message store)
    _store_message(actor_id, data.session_id, data.role, data.content)

    return {"status": "saved", "store": "sql"}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, authorization: Optional[str] = Header(None)):
    """Delete a chat session from both Memory and DynamoDB index."""
    email = _resolve_email(authorization)
    actor_id = _email_to_actor(email)

    # Remove from session index
    sessions = _get_sessions(email)
    sessions = [s for s in sessions if s["id"] != session_id]
    _save_sessions(email, sessions)

    # Delete events from AgentCore Memory
    _delete_session_events(actor_id, session_id)

    return {"status": "deleted"}
