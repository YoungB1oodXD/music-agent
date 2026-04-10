from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BEHAVIOR_TYPES = {
    "like",
    "unlike",
    "play",
    "add_to_playlist",
    "remove_from_playlist",
    "refresh_exclude",
}


def record_behavior(
    user_id: str,
    song_id: str,
    behavior_type: str,
    song_name: str = "",
    session_id: str = "",
    metadata: dict | None = None,
    db: Session | None = None,
) -> bool:
    try:
        if db is not None:
            _record_to_sqlite(
                db, user_id, song_id, behavior_type, song_name, session_id, metadata
            )
        else:
            from src.database import get_db

            db_gen = get_db()
            inner_db = next(db_gen)
            try:
                _record_to_sqlite(
                    inner_db,
                    user_id,
                    song_id,
                    behavior_type,
                    song_name,
                    session_id,
                    metadata,
                )
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
        return True
    except Exception as e:
        logger.error(f"Failed to record behavior: {e}", exc_info=True)
        return False


def _record_to_sqlite(
    db: Session,
    user_id: str,
    song_id: str,
    behavior_type: str,
    song_name: str,
    session_id: str,
    metadata: dict | None,
) -> None:
    from src.models.user_behavior import UserBehavior

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


def get_behavior_stats() -> dict:
    from src.database import get_db
    from src.models.user_behavior import UserBehavior

    try:
        db_gen = get_db()
        db = next(db_gen)
        try:
            total = db.query(UserBehavior).count()
            from sqlalchemy import func

            results = (
                db.query(
                    UserBehavior.behavior_type,
                    func.count(UserBehavior.id).label("count"),
                )
                .group_by(UserBehavior.behavior_type)
                .all()
            )
            by_type = {row.behavior_type: row.count for row in results}
            return {"total": total, "by_type": by_type}
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as e:
        logger.error(f"Failed to get behavior stats: {e}")
        return {"total": 0, "by_type": {}}
