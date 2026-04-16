from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database import get_db
from src.models import ChatHistory, User

logger = logging.getLogger(__name__)
session_router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class TurnMessage(BaseModel):
    id: str
    role: str
    content: str
    timestamp: int | float
    recommendations: List[Any] = Field(default_factory=list)


class SessionStateAPI(BaseModel):
    mood: str | None = None
    scene: str | None = None
    style: str | None = None
    energy: str | None = None
    vocal: str | None = None


class SessionDetail(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[TurnMessage]
    session_state: SessionStateAPI


class SessionSummary(BaseModel):
    session_id: str
    first_message: str
    last_message: str
    turn_count: int
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]


@session_router.get("", response_model=SessionListResponse)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    user_id_str = str(current_user.id)
    rows = (
        db.query(ChatHistory)
        .filter((ChatHistory.user_id == user_id_str) | (ChatHistory.user_id == None))
        .all()
    )

    sessions_map: dict[str, dict] = {}
    for row in rows:
        sid = row.session_id
        if sid not in sessions_map:
            sessions_map[sid] = {
                "session_id": sid,
                "first_message": "",
                "last_message": "",
                "turn_count": 0,
                "created_at": row.timestamp,
                "updated_at": row.timestamp,
            }
        entry = sessions_map[sid]
        entry["turn_count"] += 1
        if entry["first_message"] == "":
            entry["first_message"] = row.user_input
        entry["last_message"] = row.user_input
        if row.timestamp > entry["updated_at"]:
            entry["updated_at"] = row.timestamp
        if row.timestamp < entry["created_at"]:
            entry["created_at"] = row.timestamp

    sessions = [
        SessionSummary(
            session_id=data["session_id"],
            first_message=data["first_message"],
            last_message=data["last_message"],
            turn_count=data["turn_count"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
        for data in sessions_map.values()
    ]
    sessions.sort(key=lambda s: s.updated_at, reverse=True)
    logger.info(f"[SESSIONS] user={current_user.id} count={len(sessions)}")
    return SessionListResponse(sessions=sessions)


@session_router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionDetail:
    user_id_str = str(current_user.id)
    rows = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == user_id_str,
        )
        .order_by(ChatHistory.turn_id)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build messages from user_input / system_response pairs
    messages: List[TurnMessage] = []
    for i, row in enumerate(rows):
        user_turn = TurnMessage(
            id=f"{session_id}-{i}-u",
            role="user",
            content=row.user_input,
            timestamp=int(row.timestamp.timestamp() * 1000),
        )
        messages.append(user_turn)
        if row.system_response:
            assistant_turn = TurnMessage(
                id=f"{session_id}-{i}-a",
                role="assistant",
                content=row.system_response,
                timestamp=int(row.timestamp.timestamp() * 1000) + 1,
            )
            messages.append(assistant_turn)

    first = rows[0]
    last = rows[-1]
    # Derive session state from first user message entities if available
    entities = rows[0].entities or {}
    session_state = SessionStateAPI(
        mood=entities.get("mood"),
        scene=entities.get("scene"),
        style=entities.get("genre"),
        energy=entities.get("energy"),
        vocal=entities.get("vocal"),
    )
    logger.info(
        f"[SESSIONS] get session={session_id} for user={current_user.id} turns={len(rows)}"
    )
    return SessionDetail(
        session_id=session_id,
        title=first.user_input[:30] + ("..." if len(first.user_input) > 30 else ""),
        created_at=first.timestamp,
        updated_at=last.timestamp,
        messages=messages,
        session_state=session_state,
    )


@session_router.delete("/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user_id_str = str(current_user.id)
    count = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.user_id == user_id_str,
        )
        .count()
    )
    if count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == user_id_str,
    ).delete()
    db.commit()
    logger.info(f"[SESSIONS] deleted session={session_id} for user={current_user.id}")
    return {"ok": True}
