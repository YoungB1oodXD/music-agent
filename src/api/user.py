from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database import get_db
from src.models import User
from src.models.user_preference import UserPreference
from src.models.user_behavior import UserBehavior

logger = logging.getLogger(__name__)
user_router = APIRouter(prefix="/api/user", tags=["user"])


class UserPreferenceResponse(BaseModel):
    user_id: int
    preferred_genres: list[str] = Field(default_factory=list)
    preferred_energy: Optional[str] = None
    preferred_vocals: Optional[str] = None
    updated_at: datetime


class UpdatePreferenceRequest(BaseModel):
    preferred_genres: Optional[list[str]] = None
    preferred_energy: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    preferred_vocals: Optional[str] = Field(None, pattern="^(instrumental|vocal)$")


class BehaviorRecord(BaseModel):
    id: int
    song_id: str
    behavior_type: str
    song_name: str
    session_id: str
    metadata_json: dict
    created_at: datetime


class BehaviorListResponse(BaseModel):
    total: int
    records: List[BehaviorRecord]
    page: int
    page_size: int
    total_pages: int


@user_router.get("/preferences", response_model=UserPreferenceResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferenceResponse:
    pref = UserPreference.get_or_create(db, current_user.id)
    return UserPreferenceResponse(
        user_id=pref.user_id,
        preferred_genres=pref.preferred_genres or [],
        preferred_energy=pref.preferred_energy,
        preferred_vocals=pref.preferred_vocals,
        updated_at=pref.updated_at,
    )


@user_router.put("/preferences", response_model=UserPreferenceResponse)
def update_preferences(
    req: UpdatePreferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPreferenceResponse:
    pref = UserPreference.update_preferences(
        db,
        current_user.id,
        preferred_genres=req.preferred_genres,
        preferred_energy=req.preferred_energy,
        preferred_vocals=req.preferred_vocals,
    )
    logger.info(f"[USER PREFERENCES] updated user={current_user.id}")
    return UserPreferenceResponse(
        user_id=pref.user_id,
        preferred_genres=pref.preferred_genres or [],
        preferred_energy=pref.preferred_energy,
        preferred_vocals=pref.preferred_vocals,
        updated_at=pref.updated_at,
    )


@user_router.get("/behaviors", response_model=BehaviorListResponse)
def list_behaviors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    behavior_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> BehaviorListResponse:
    user_id_str = str(current_user.id)
    query = db.query(UserBehavior).filter(UserBehavior.user_id == user_id_str)

    if behavior_type:
        query = query.filter(UserBehavior.behavior_type == behavior_type)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size

    records = (
        query.order_by(UserBehavior.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    logger.info(
        f"[BEHAVIORS] user={current_user.id} type={behavior_type} "
        f"page={page} count={len(records)}"
    )

    return BehaviorListResponse(
        total=total,
        records=[
            BehaviorRecord(
                id=r.id,
                song_id=r.song_id,
                behavior_type=r.behavior_type,
                song_name=r.song_name,
                session_id=r.session_id,
                metadata_json=r.metadata_json or {},
                created_at=r.created_at,
            )
            for r in records
        ],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
