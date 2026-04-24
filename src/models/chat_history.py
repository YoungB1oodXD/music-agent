from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON
from sqlalchemy.orm import Session

from src.database.db import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    turn_id = Column(Integer, nullable=False)
    user_input = Column(String(2000), nullable=False)
    system_response = Column(String(5000), nullable=False)
    intent = Column(String(50), nullable=True)
    entities = Column(JSON, default=dict)
    recommendations = Column(JSON, default=list)
    timestamp = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def save_turns(
        db: Session,
        session_id: str,
        user_id: str | None,
        turns: list[dict],
    ) -> None:
        for turn_data in turns:
            entry = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                turn_id=turn_data["turn_id"],
                user_input=turn_data["user_input"],
                system_response=turn_data["system_response"],
                intent=turn_data.get("intent"),
                entities=turn_data.get("entities", {}),
                recommendations=turn_data.get("recommendations", []),
            )
            db.add(entry)
        db.commit()

    @staticmethod
    def load_history(
        db: Session, session_id: str, user_id: str | None = None
    ) -> list[ChatHistory]:
        query = db.query(ChatHistory).filter(ChatHistory.session_id == session_id)
        if user_id is not None:
            query = query.filter(ChatHistory.user_id == user_id)
        return query.order_by(ChatHistory.turn_id).all()

    @staticmethod
    def clear_history(db: Session, session_id: str, user_id: str | None = None) -> None:
        query = db.query(ChatHistory).filter(ChatHistory.session_id == session_id)
        if user_id is not None:
            query = query.filter(ChatHistory.user_id == user_id)
        query.delete()
        db.commit()
