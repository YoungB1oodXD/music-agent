"""
智能用户画像 API 路由

接口：
- POST /api/ai/generate-portrait - 生成用户画像
- GET /api/ai/portrait - 获取缓存的画像（含流派偏好）
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database.db import get_db
from src.models.user import User
from src.models.user_preference import UserPreference
from src.services.portrait_service import PortraitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


class PortraitResponse(BaseModel):
    # 基础画像字段
    user_id: int
    summary: str
    keywords: list[str]
    scene: str
    generated_at: Optional[str] = None

    # 流派偏好数据
    liked_genres: list[str]
    disliked_genres: list[str]
    liked_genre_counts: dict[str, int]
    disliked_genre_counts: dict[str, int]

    # 能量/声乐偏好
    preferred_energy: str
    preferred_vocals: str

    # LLM 深度分析（按需生成，不缓存）
    deep_analysis: Optional[str] = None

    # 更新时间
    updated_at: Optional[str] = None


class GeneratePortraitRequest(BaseModel):
    # 无需参数，从 session 获取 user_id
    pass


def _build_portrait_response(
    prefs: UserPreference,
    portrait: dict,
) -> PortraitResponse:
    """从 UserPreference 构建完整的 PortraitResponse"""
    liked = prefs.liked_genre_counts or {}
    disliked = prefs.disliked_genre_counts or {}

    # 从 energy_scores 推导 preferred_energy
    energy_data = prefs.energy_scores or {}
    scores = energy_data.get("scores", [])
    if scores:
        from src.models.user_preference import ENERGY_REVERSE_MAP
        from collections import Counter

        most_common = Counter(scores).most_common(1)
        if most_common:
            preferred_energy = ENERGY_REVERSE_MAP.get(most_common[0][0], "none")
        else:
            preferred_energy = "none"
    else:
        preferred_energy = "none"

    # 从 vocal_scores 推导 preferred_vocals
    vocal_data = prefs.vocal_scores or {}
    vocal_scores = vocal_data.get("scores", [])
    if vocal_scores:
        # 1 = 人声为主, 0 = 纯器乐
        preferred_vocals = "with_vocals" if sum(vocal_scores) > 0 else "no_vocals"
    else:
        preferred_vocals = "no_preference"

    # 计算总数
    total_likes = sum(liked.values()) if liked else 0
    total_dislikes = sum(disliked.values()) if disliked else 0

    return PortraitResponse(
        user_id=prefs.user_id,
        summary=portrait.get("summary", ""),
        keywords=portrait.get("keywords", []),
        scene=portrait.get("scene", ""),
        generated_at=portrait.get("generated_at"),
        liked_genres=list(liked.keys()),
        disliked_genres=list(disliked.keys()),
        liked_genre_counts=liked,
        disliked_genre_counts=disliked,
        preferred_energy=preferred_energy,
        preferred_vocals=preferred_vocals,
        deep_analysis=portrait.get("deep_analysis"),
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


@router.post("/generate-portrait", response_model=PortraitResponse)
def generate_portrait(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    生成用户画像

    1. 读取用户偏好和喜欢歌单
    2. 获取对话历史和场景偏好
    3. 调用 LLM 生成画像和深度分析
    4. 缓存到数据库
    """
    from src.api.app import ORCHESTRATOR

    service = PortraitService(llm_client=ORCHESTRATOR.llm)
    portrait = service.generate_portrait(
        db=db, user_id=current_user.id, session_id=session_id
    )

    prefs = UserPreference.get_or_create(db, current_user.id)

    return _build_portrait_response(prefs, portrait)


@router.get("/portrait", response_model=PortraitResponse)
def get_portrait(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前缓存的用户画像（含流派偏好）"""
    from src.api.app import ORCHESTRATOR

    service = PortraitService(llm_client=ORCHESTRATOR.llm)
    cached = service.get_cached_portrait(db=db, user_id=current_user.id)

    if not cached or not cached.get("summary"):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="请先生成用户画像")

    prefs = UserPreference.get_or_create(db, current_user.id)

    portrait = dict(cached)

    if session_id and not portrait.get("deep_analysis"):
        liked_songs = service._get_liked_songs(db, current_user.id, limit=20)
        dialogue_history = service._get_dialogue_history(db, session_id)
        preferred_scenes = service._get_preferred_scenes(db, session_id)
        try:
            deep = service._call_llm_deep_analysis(
                prefs, liked_songs, dialogue_history, preferred_scenes
            )
            if deep:
                portrait["deep_analysis"] = deep.get("deep_analysis", "")
                if deep.get("scene"):
                    portrait["scene"] = deep["scene"]
                prefs.ai_portrait_deep_analysis = portrait["deep_analysis"]
                if deep.get("scene"):
                    prefs.ai_portrait_scene = deep["scene"]
                prefs.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning(f"[Portrait] 深度分析生成失败: {e}")

    return _build_portrait_response(prefs, portrait)


@router.delete("/portrait")
def clear_portrait(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清除当前用户的画像缓存"""
    prefs = UserPreference.get_or_create(db, current_user.id)
    prefs.ai_portrait_summary = ""
    prefs.ai_portrait_keywords = []
    prefs.ai_portrait_scene = ""
    prefs.ai_portrait_deep_analysis = ""
    prefs.ai_portrait_generated_at = None
    prefs.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"[Portrait] Cleared portrait for user_id={current_user.id}")
    return {"ok": True}
