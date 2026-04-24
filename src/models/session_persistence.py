from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.orm import Session

from src.database.db import Base


class SessionPersistence(Base):
    __tablename__ = "session_persistence"

    session_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=True, index=True)

    current_mood = Column(String(50), nullable=True)
    current_scene = Column(String(50), nullable=True)
    current_genre = Column(String(50), nullable=True)

    preference_profile = Column(JSON, default=dict)

    liked_songs = Column(JSON, default=list)
    disliked_songs = Column(JSON, default=list)
    exclude_ids = Column(JSON, default=list)
    exclude_artists = Column(JSON, default=list)

    preferred_moods = Column(JSON, default=list)
    preferred_scenes = Column(JSON, default=list)

    last_recommendation_query = Column(String(500), nullable=True)
    last_recommendation_results = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_or_create(
        db: Session, session_id: str, user_id: str | None = None
    ) -> "SessionPersistence":
        record = (
            db.query(SessionPersistence)
            .filter(SessionPersistence.session_id == session_id)
            .first()
        )
        if record is None:
            record = SessionPersistence(
                session_id=session_id,
                user_id=user_id,
                current_mood=None,
                current_scene=None,
                current_genre=None,
                preference_profile={},
                liked_songs=[],
                disliked_songs=[],
                exclude_ids=[],
                exclude_artists=[],
                preferred_moods=[],
                preferred_scenes=[],
                last_recommendation_query=None,
                last_recommendation_results=[],
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        return record

    @staticmethod
    def load_from_db(db: Session, session_id: str) -> "SessionPersistence | None":
        return (
            db.query(SessionPersistence)
            .filter(SessionPersistence.session_id == session_id)
            .first()
        )

    def apply_to_state(self, state: "SessionState") -> None:
        from src.manager.session_state import SessionState as SS

        state.current_mood = self.current_mood
        state.current_scene = self.current_scene
        state.current_genre = self.current_genre

        if self.preference_profile:
            pf = state.preference_profile
            pf.preferred_genres = self.preference_profile.get("preferred_genres", [])
            pf.disliked_genres = self.preference_profile.get("disliked_genres", [])
            pf.preferred_energy = self.preference_profile.get("preferred_energy")
            pf.preferred_vocals = self.preference_profile.get("preferred_vocals")

        state.liked_songs = self.liked_songs or []
        state.disliked_songs = self.disliked_songs or []
        state.exclude_ids = self.exclude_ids or []
        state.exclude_artists = self.exclude_artists or []
        state.preferred_moods = self.preferred_moods or []
        state.preferred_scenes = self.preferred_scenes or []

        if self.last_recommendation_results:
            from src.manager.session_state import (
                RecommendationItem,
                RecommendationRecord,
            )

            results = [
                RecommendationItem(
                    id=r.get("id", ""), name=r.get("name", ""), reason=r.get("reason")
                )
                for r in self.last_recommendation_results
            ]
            state.last_recommendation = RecommendationRecord(
                query=self.last_recommendation_query or "",
                results=results,
                method="hybrid",
            )

    @staticmethod
    def state_to_dict(state: "SessionState") -> dict:
        return {
            "current_mood": state.current_mood,
            "current_scene": state.current_scene,
            "current_genre": state.current_genre,
            "preference_profile": {
                "preferred_genres": state.preference_profile.preferred_genres,
                "disliked_genres": state.preference_profile.disliked_genres,
                "preferred_energy": state.preference_profile.preferred_energy,
                "preferred_vocals": state.preference_profile.preferred_vocals,
            },
            "liked_songs": state.liked_songs,
            "disliked_songs": state.disliked_songs,
            "exclude_ids": state.exclude_ids[:100],
            "exclude_artists": state.exclude_artists,
            "preferred_moods": state.preferred_moods,
            "preferred_scenes": state.preferred_scenes,
            "last_recommendation_query": state.last_recommendation.query
            if state.last_recommendation
            else None,
            "last_recommendation_results": (
                [
                    {"id": r.id, "name": r.name, "reason": r.reason}
                    for r in state.last_recommendation.results
                ]
                if state.last_recommendation
                else []
            ),
        }
