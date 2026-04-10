import logging
from collections.abc import Mapping
from typing import TypedDict, cast

from .cf_recommend_tool import cf_recommend
from .semantic_search_tool import _derive_explanation_fields, semantic_search


logger = logging.getLogger(__name__)


HYBRID_RECOMMEND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "seed_song_name": {"type": "string"},
        "top_k": {"type": "integer"},
        "w_sem": {"type": "number"},
        "w_cf": {"type": "number"},
        "exclude_ids": {"type": "array"},
        "intent": {"type": "string"},
    },
    "required": ["query_text", "top_k"],
}


_HYBRID_CANDIDATE_CAP = 40
_HYBRID_CANDIDATE_MULTIPLIER = 4
_MIN_SEMANTIC_SIMILARITY = 0.26
_HARD_MIN_SEMANTIC_SIMILARITY = 0.18

_CF_SIGNAL_THRESHOLD = 1e-6
_CF_SCORE_SPREAD_THRESHOLD = 1e-8


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
    cf_score: object
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


def _split_name(display_name: str) -> dict[str, str]:
    if " - " in display_name:
        artist, title = display_name.split(" - ", 1)
        return {"artist": artist.strip(), "title": title.strip()}
    return {"artist": "", "title": display_name}


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


def _compute_cf_signal_strength(cf_items: list["ScoredItem"]) -> dict[str, float]:
    if not cf_items:
        return {"mean": 0.0, "spread": 0.0, "max": 0.0}
    scores = [_to_float(item.get("score", 0.0), 0.0) for item in cf_items]
    mean_score = sum(scores) / len(scores) if scores else 0.0
    spread = max(scores) - min(scores) if scores else 0.0
    return {"mean": mean_score, "spread": spread, "max": max(scores) if scores else 0.0}


def _get_intent_weights(
    intent: str | None, cf_signal: dict[str, float]
) -> tuple[float, float]:
    cf_mean = cf_signal.get("mean", 0.0)
    cf_spread = cf_signal.get("spread", 0.0)

    if cf_mean < _CF_SIGNAL_THRESHOLD or cf_spread < _CF_SCORE_SPREAD_THRESHOLD:
        logger.info(
            f"CF signal too weak (mean={cf_mean:.2e}, spread={cf_spread:.2e}), "
            f"falling back to semantic-only"
        )
        return (1.0, 0.0)

    if intent == "similar_to_last":
        logger.info(
            f"Intent=similar_to_last, using behavior-prioritized weights (0.4/0.6)"
        )
        return (0.4, 0.6)
    elif intent == "search":
        logger.info(f"Intent=search, using semantic-only weights (1.0/0.0)")
        return (1.0, 0.0)
    elif intent == "recommend":
        logger.info(f"Intent=recommend, using balanced weights (0.7/0.3)")
        return (0.7, 0.3)
    else:
        logger.info(f"Intent=default, using balanced weights (0.7/0.3)")
        return (0.7, 0.3)


def hybrid_recommend(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    top_k = max(1, _to_int(args["top_k"], default=5))
    sem_top_k = min(_HYBRID_CANDIDATE_CAP, top_k * _HYBRID_CANDIDATE_MULTIPLIER)
    cf_top_k = min(_HYBRID_CANDIDATE_CAP, top_k * _HYBRID_CANDIDATE_MULTIPLIER)
    exclude_ids = _parse_exclude_ids(args)
    seed_song_name_obj = args.get("seed_song_name")
    seed_song_name = str(seed_song_name_obj) if seed_song_name_obj is not None else None
    intent_obj = args.get("intent")
    intent = str(intent_obj) if intent_obj is not None else None

    manual_w_sem = args.get("w_sem")
    manual_w_cf = args.get("w_cf")
    use_manual_weights = manual_w_sem is not None or manual_w_cf is not None

    w_sem = 0.7
    w_cf = 0.3

    if use_manual_weights:
        w_sem = _to_float(args.get("w_sem", 0.6), 0.6)
        w_cf = _to_float(args.get("w_cf", 0.4), 0.4)
        logger.info(f"Using manual weights: w_sem={w_sem}, w_cf={w_cf}")

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

    cf_items: list[ScoredItem] = []
    if seed_song_name:
        cf_result = cf_recommend(
            {
                "song_name": seed_song_name,
                "top_k": cf_top_k,
                "exclude_ids": list(exclude_ids),
            }
        )
        cf_data = cf_result.get("data", {})
        if not isinstance(cf_data, dict):
            cf_data = {}
        cf_data = cast(dict[str, object], cf_data)
        recommendations = cf_data.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        recommendations = cast(list[object], recommendations)

        if cf_result.get("ok") is not True and not recommendations:
            logger.info(
                f"CF failed for seed='{seed_song_name}': {cf_result.get('error', 'unknown')}. "
                f"Falling back to semantic-only."
            )

        for rec_obj in recommendations:
            if not isinstance(rec_obj, dict):
                continue
            rec = cast(dict[str, object], rec_obj)
            rec_id = str(rec.get("id") or "")
            if not rec_id:
                continue
            cf_items.append(
                {
                    "id": rec_id,
                    "score": _to_float(rec.get("score"), 0.0),
                    "payload": rec,
                }
            )

    if not use_manual_weights:
        cf_signal = _compute_cf_signal_strength(cf_items)
        w_sem, w_cf = _get_intent_weights(intent, cf_signal)

    sem_norm = _normalize_scores(sem_scored, "score")
    cf_norm = _normalize_scores(cf_items, "score")

    merged: dict[str, HybridItem] = {}

    for row in sem_scored:
        item_id = row["id"]
        payload = row["payload"]
        merged[item_id] = {
            "id": payload.get("id"),
            "title": payload.get("title"),
            "artist": payload.get("artist"),
            "genre": payload.get("genre"),
            "track_id": payload.get("track_id"),
            "semantic_similarity": payload.get("similarity"),
            "distance": payload.get("distance"),
            "cf_score": None,
            "score": w_sem * sem_norm.get(item_id, 0.0),
            "sources": ["semantic"],
            "is_playable": payload.get("is_playable"),
            "audio_url": payload.get("audio_url"),
            "genre_description": payload.get("genre_description"),
            "mood_tags": payload.get("mood_tags"),
            "scene_tags": payload.get("scene_tags"),
            "instrumentation": payload.get("instrumentation"),
            "energy_note": payload.get("energy_note"),
        }

    for row in cf_items:
        item_id = row["id"]
        payload = row["payload"]
        split = _split_name(str(payload.get("name", "")))
        cf_genre = payload.get("genre") or ""
        explanation = _derive_explanation_fields(str(cf_genre)) if cf_genre else {}
        if item_id not in merged:
            merged[item_id] = {
                "id": payload.get("id"),
                "title": split["title"],
                "artist": split["artist"],
                "genre": cf_genre,
                "track_id": payload.get("id"),
                "semantic_similarity": None,
                "distance": None,
                "cf_score": payload.get("score"),
                "score": w_cf * cf_norm.get(item_id, 0.0),
                "sources": ["cf"],
                "is_playable": payload.get("is_playable"),
                "audio_url": payload.get("audio_url"),
                "genre_description": explanation.get("genre_description"),
                "mood_tags": explanation.get("mood_tags"),
                "scene_tags": explanation.get("scene_tags"),
                "instrumentation": explanation.get("instrumentation"),
                "energy_note": explanation.get("energy_note"),
            }
        else:
            merged[item_id]["cf_score"] = payload.get("score")
            merged[item_id]["score"] = merged[item_id]["score"] + w_cf * cf_norm.get(
                item_id, 0.0
            )
            sources = merged[item_id]["sources"]
            if "cf" not in sources:
                sources.append("cf")

    ranked = sorted(merged.values(), key=lambda row: row["score"], reverse=True)
    if exclude_ids:
        filtered_ranked: list[HybridItem] = []
        for row in ranked:
            comparable_ids = _collect_result_ids(row)
            if comparable_ids and comparable_ids.intersection(exclude_ids):
                continue
            filtered_ranked.append(row)
        ranked = filtered_ranked

    return {"ok": True, "data": ranked[:top_k]}
