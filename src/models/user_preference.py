from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Session

from src.database.db import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    preferred_genres = Column(JSON, default=list)
    preferred_energy = Column(String(20), default=None)
    preferred_vocals = Column(String(20), default=None)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_or_create(db: Session, user_id: int) -> "UserPreference":
        pref = (
            db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        )
        if pref is None:
            pref = UserPreference(
                user_id=user_id,
                preferred_genres=[],
                preferred_energy=None,
                preferred_vocals=None,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_preferences(
        db: Session,
        user_id: int,
        preferred_genres: list[str] | None = None,
        preferred_energy: str | None = None,
        preferred_vocals: str | None = None,
    ) -> "UserPreference":
        pref = UserPreference.get_or_create(db, user_id)
        if preferred_genres is not None:
            pref.preferred_genres = preferred_genres
        if preferred_energy is not None:
            pref.preferred_energy = preferred_energy
        if preferred_vocals is not None:
            pref.preferred_vocals = preferred_vocals
        pref.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(pref)
        return pref
