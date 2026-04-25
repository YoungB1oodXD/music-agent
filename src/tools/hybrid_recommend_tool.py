import logging
from collections.abc import Mapping
from typing import TypedDict, cast

from .semantic_search_tool import semantic_search


logger = logging.getLogger(__name__)


HYBRID_RECOMMEND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
        "exclude_ids": {"type": "array"},
        "intent": {"type": "string"},
        "user_id": {"type": "string"},  # string类型，orchestrator传递的是字符串
    },
    "required": ["query_text", "top_k"],
}


_HYBRID_CANDIDATE_CAP = 40
_HYBRID_CANDIDATE_MULTIPLIER = 4
_MIN_SEMANTIC_SIMILARITY = 0.26
_HARD_MIN_SEMANTIC_SIMILARITY = 0.18


class ScoredItem(TypedDict):
    id: str
    score: float
    payload: dict[str, object]


class HybridItem(TypedDict):
    id: object
    title: object
    artist: object
    genre: object
    track_id: object
    semantic_similarity: object
    distance: object
    score: float
    sources: list[str]
    is_playable: object
    audio_url: object
    genre_description: object
    mood_tags: object
    scene_tags: object
    instrumentation: object
    energy_note: object


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(cast(float | int | str, value))
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(cast(int | float | str, value))
    except (TypeError, ValueError):
        return default


def _normalize_scores(items: list[ScoredItem], score_key: str) -> dict[str, float]:
    values = [_to_float(item.get(score_key, 0.0), 0.0) for item in items]
    if not values:
        return {}

    min_score = min(values)
    max_score = max(values)
    spread = max_score - min_score

    normalized: dict[str, float] = {}
    for item in items:
        item_id = str(item.get("id", ""))
        if not item_id:
            continue
        raw = _to_float(item.get(score_key, 0.0), 0.0)
        if spread <= 0:
            normalized[item_id] = 1.0 if raw > 0 else 0.0
        else:
            normalized[item_id] = (raw - min_score) / spread
    return normalized


def _parse_exclude_ids(args: dict[str, object]) -> set[str]:
    raw_obj = args.get("exclude_ids")
    if not isinstance(raw_obj, list):
        return set()

    raw = cast(list[object], raw_obj)
    parsed: set[str] = set()
    for value_obj in raw:
        if not isinstance(value_obj, str):
            continue
        normalized = value_obj.strip()
        if normalized:
            parsed.add(normalized)
    return parsed


def _collect_result_ids(item: Mapping[str, object]) -> set[str]:
    comparable_ids: set[str] = set()
    for key in ("track_id", "id"):
        value = item.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int, float)):
            normalized = str(value).strip()
            if normalized:
                comparable_ids.add(normalized)
    return comparable_ids


def _load_user_preference(user_id: str | int) -> dict | None:
    """加载用户偏好设置"""
    try:
        from src.database.db import get_db
        from src.models.user_preference import UserPreference

        # 转换为 int（如果需要）
        if isinstance(user_id, str):
            if not user_id.isdigit():
                return None
            user_id = int(user_id)

        db_gen = get_db()
        db = next(db_gen)
        try:
            pref = UserPreference.get_or_create(db, user_id)
            return {
                "liked_genres": pref.liked_genre_counts or {},
                "disliked_genres": pref.disliked_genre_counts or {},
            }
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as e:
        logger.warning(f"[PREFERENCE] Failed to load preference: {e}")
        return None


def _apply_genre_adjustment(
    score: float, genre: str, user_prefs: dict | None, dislike_threshold: int = 3
) -> float:
    """
    应用流派偏好调整（加法融合）
    - liked genres: +0.03 ~ +0.15
    - disliked genres (>= threshold): -0.1 ~ -0.2
    """
    if not user_prefs:
        return score

    liked = user_prefs.get("liked_genres", {})
    disliked = user_prefs.get("disliked_genres", {})

    # 喜欢加分
    like_count = liked.get(genre, 0)
    if like_count > 0:
        adjustment = min(0.15, like_count * 0.03)  # 最多加 0.15
        score += adjustment

    # 不喜欢减分（需要超过阈值）
    dislike_count = disliked.get(genre, 0)
    if dislike_count >= dislike_threshold:
        adjustment = -min(0.2, dislike_count * 0.05)  # 3次→-0.15, 4次→-0.2
        score += adjustment

    return score


def hybrid_recommend(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    top_k = max(1, _to_int(args["top_k"], default=5))
    sem_top_k = min(_HYBRID_CANDIDATE_CAP, top_k * _HYBRID_CANDIDATE_MULTIPLIER)
    exclude_ids = _parse_exclude_ids(args)

    # 加载用户偏好（新增）
    user_id = args.get("user_id")
    user_prefs = None
    if user_id:
        user_prefs = _load_user_preference(user_id)
        if user_prefs:
            logger.info(
                f"[Hybrid] Loaded user preferences: liked={len(user_prefs.get('liked_genres', {}))}, disliked={len(user_prefs.get('disliked_genres', {}))}"
            )

    logger.info(
        f"[Hybrid] query='{query_text}', top_k={top_k}, exclude={len(exclude_ids)}"
    )

    sem_result = semantic_search(
        {"query_text": query_text, "top_k": sem_top_k, "exclude_ids": list(exclude_ids)}
    )
    if sem_result.get("ok") is not True:
        return {
            "ok": False,
            "data": [],
            "error": sem_result.get("error", "Semantic search failed"),
        }

    sem_items = sem_result.get("data", [])
    sem_scored_raw: list[ScoredItem] = []
    if not isinstance(sem_items, list):
        sem_items = []
    sem_items = cast(list[object], sem_items)

    for item_obj in sem_items:
        if not isinstance(item_obj, dict):
            continue
        item = cast(dict[str, object], item_obj)
        item_id = str(item.get("track_id") or item.get("id") or "")
        if not item_id:
            continue
        sem_scored_raw.append(
            {
                "id": item_id,
                "score": _to_float(item.get("similarity"), 0.0),
                "payload": item,
            }
        )

    sem_scored: list[ScoredItem] = []
    sem_floor_passed: list[ScoredItem] = []
    for row in sem_scored_raw:
        if row["score"] >= _MIN_SEMANTIC_SIMILARITY:
            sem_scored.append(row)
        elif row["score"] >= _HARD_MIN_SEMANTIC_SIMILARITY:
            sem_floor_passed.append(row)
    if len(sem_scored) < sem_top_k:
        for row in sem_floor_passed:
            sem_scored.append(row)
            if len(sem_scored) >= sem_top_k:
                break
    if not sem_scored and sem_scored_raw:
        sem_scored = [sem_scored_raw[0]]

    logger.info(f"[Hybrid] semantic candidates: {len(sem_scored)}")

    sem_norm = _normalize_scores(sem_scored, "score")

    merged: dict[str, HybridItem] = {}

    for row in sem_scored:
        item_id = row["id"]
        payload = row["payload"]

        # 计算基础分数
        base_score = sem_norm.get(item_id, 0.0)

        # 应用流派偏好调整（加法融合，新增）
        genre = str(payload.get("genre") or "")
        adjusted_score = _apply_genre_adjustment(base_score, genre, user_prefs)

        merged[item_id] = {
            "id": payload.get("id"),
            "title": payload.get("title"),
            "artist": payload.get("artist"),
            "genre": payload.get("genre"),
            "track_id": payload.get("track_id"),
            "semantic_similarity": payload.get("similarity"),
            "distance": payload.get("distance"),
            "score": adjusted_score,
            "base_score": base_score,  # 保留原始分数用于调试
            "preference_adjustment": adjusted_score - base_score,  # 偏好调整量
            "sources": ["semantic"],
            "is_playable": payload.get("is_playable"),
            "audio_url": payload.get("audio_url"),
            "genre_description": payload.get("genre_description"),
            "style": payload.get("style"),
            "mood_tags": payload.get("mood_tags"),
            "scene_tags": payload.get("scene_tags"),
            "instrumentation": payload.get("instrumentation"),
            "energy_note": payload.get("energy_note"),
        }

    ranked = sorted(merged.values(), key=lambda row: row["score"], reverse=True)
    if exclude_ids:
        filtered_ranked: list[HybridItem] = []
        for row in ranked:
            comparable_ids = _collect_result_ids(row)
            if comparable_ids and comparable_ids.intersection(exclude_ids):
                continue
            filtered_ranked.append(row)
        ranked = filtered_ranked

    logger.info(f"[Hybrid] returning {min(top_k, len(ranked))} results")
    return {"ok": True, "data": ranked[:top_k]}
