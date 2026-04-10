from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON
from sqlalchemy.orm import Session

from src.database.db import Base


class UserBehavior(Base):
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    song_id = Column(String(50), nullable=False, index=True)
    behavior_type = Column(String(30), nullable=False)
    song_name = Column(String(200), default="")
    session_id = Column(String(50), default="")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def record(
        db: Session,
        user_id: str,
        song_id: str,
        behavior_type: str,
        song_name: str = "",
        session_id: str = "",
        metadata: dict | None = None,
    ) -> "UserBehavior":
        entry = UserBehavior(
            user_id=user_id,
            song_id=song_id,
            behavior_type=behavior_type,
            song_name=song_name,
            session_id=session_id,
            metadata_json=metadata or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_user_behaviors(
        db: Session, user_id: str, behavior_type: str | None = None, limit: int = 100
    ) -> list["UserBehavior"]:
        query = db.query(UserBehavior).filter(UserBehavior.user_id == user_id)
        if behavior_type:
            query = query.filter(UserBehavior.behavior_type == behavior_type)
        return query.order_by(UserBehavior.created_at.desc()).limit(limit).all()
