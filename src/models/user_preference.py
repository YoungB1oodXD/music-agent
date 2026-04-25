from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Session

from src.database.db import Base

# Energy 映射：用于加权平均计算
ENERGY_MAP = {"high": 3, "medium": 2, "low": 1, "none": 0}
ENERGY_REVERSE_MAP = {3: "high", 2: "medium", 1: "low", 0: "none"}


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    # 喜欢的流派及计数：{"Rock": 5, "Jazz": 3}
    liked_genre_counts = Column(JSON, default=dict)

    # 不喜欢的流派及计数：{"Metal": 2, "Country": 1}
    disliked_genre_counts = Column(JSON, default=dict)

    # 能量偏好：{"scores": [3, 2, 3], "count": 3} -> average = (3+2+3)/3 = 2.67 -> round -> "medium"
    energy_scores = Column(JSON, default=dict)  # {"scores": [3, 2], "count": 2}

    # 声乐偏好：同上
    vocal_scores = Column(JSON, default=dict)  # {"scores": [1, 1], "count": 2}

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_or_create(db: Session, user_id: int) -> "UserPreference":
        pref = (
            db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        )
        if pref is None:
            pref = UserPreference(
                user_id=user_id,
                liked_genre_counts={},
                disliked_genre_counts={},
                energy_scores={"scores": [], "count": 0},
                vocal_scores={"scores": [], "count": 0},
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def record_like(
        db: Session, user_id: int, genre: str, energy: str = None
    ) -> "UserPreference":
        """
        记录用户的喜欢反馈
        - genre: 歌曲流派
        - energy: 歌曲能量值 (high/medium/low)
        """
        pref = UserPreference.get_or_create(db, user_id)

        # 更新 liked_genre_counts（使用 set 避免重复）
        liked = dict(pref.liked_genre_counts or {})
        liked[genre] = liked.get(genre, 0) + 1
        pref.liked_genre_counts = liked

        # 更新 energy_scores（加权平均）
        if energy and energy in ENERGY_MAP:
            energy_data = dict(pref.energy_scores or {"scores": [], "count": 0})
            energy_data["scores"] = energy_data.get("scores", []) + [ENERGY_MAP[energy]]
            energy_data["count"] = energy_data.get("count", 0) + 1
            pref.energy_scores = energy_data

        pref.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def record_dislike(db: Session, user_id: int, genre: str) -> "UserPreference":
        """
        记录用户的不喜欢反馈
        """
        pref = UserPreference.get_or_create(db, user_id)

        # 更新 disliked_genre_counts
        disliked = dict(pref.disliked_genre_counts or {})
        disliked[genre] = disliked.get(genre, 0) + 1
        pref.disliked_genre_counts = disliked

        pref.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(pref)
        return pref

    def get_preferred_genres(self, top_n: int = 3) -> list[str]:
        """获取用户最喜欢的流派（Top N）"""
        counts = self.liked_genre_counts or {}
        if not counts:
            return []
        sorted_genres = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [g for g, _ in sorted_genres[:top_n]]

    def get_disliked_genres(self, min_count: int = 1) -> dict[str, int]:
        """获取用户不喜欢的流派及其计数"""
        return self.disliked_genre_counts or {}

    def get_preferred_energy(self) -> str:
        """获取用户偏好的能量值（众数）"""
        energy_data = self.energy_scores or {}
        scores = energy_data.get("scores", [])
        if not scores:
            return "none"
        # 返回众数
        from collections import Counter

        most_common = Counter(scores).most_common(1)
        if most_common:
            return ENERGY_REVERSE_MAP.get(most_common[0][0], "none")
        return "none"

    def get_genre_adjustment(self, genre: str, dislike_threshold: int = 3) -> float:
        """
        获取流派调整值（用于推荐评分）
        - 正值：喜欢该流派，加分
        - 负值：不喜欢该流派，减分
        """
        # 喜欢加分
        liked = self.liked_genre_counts or {}
        like_count = liked.get(genre, 0)
        if like_count > 0:
            # 最多加 0.15 分
            return min(0.15, like_count * 0.03)

        # 不喜欢减分（需要超过阈值）
        disliked = self.disliked_genre_counts or {}
        dislike_count = disliked.get(genre, 0)
        if dislike_count >= dislike_threshold:
            # 3次以上开始减分，最多减 0.2 分
            return -min(0.2, dislike_count * 0.05)

        return 0.0
