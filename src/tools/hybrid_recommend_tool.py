from typing import TypedDict, cast

from .cf_recommend_tool import cf_recommend
from .semantic_search_tool import semantic_search


HYBRID_RECOMMEND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "seed_song_name": {"type": "string"},
        "top_k": {"type": "integer"},
        "w_sem": {"type": "number"},
        "w_cf": {"type": "number"},
    },
    "required": ["query_text", "top_k"],
}


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


def hybrid_recommend(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    top_k = _to_int(args["top_k"])
    seed_song_name_obj = args.get("seed_song_name")
    seed_song_name = str(seed_song_name_obj) if seed_song_name_obj is not None else None
    w_sem = _to_float(args.get("w_sem", 0.6), 0.6)
    w_cf = _to_float(args.get("w_cf", 0.4), 0.4)

    sem_result = semantic_search({"query_text": query_text, "top_k": top_k})
    if sem_result.get("ok") is not True:
        return {"ok": False, "data": [], "error": sem_result.get("error", "Semantic search failed")}

    sem_items = sem_result.get("data", [])
    sem_scored: list[ScoredItem] = []
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
        sem_scored.append({"id": item_id, "score": _to_float(item.get("similarity"), 0.0), "payload": item})

    cf_items: list[ScoredItem] = []
    if seed_song_name:
        cf_result = cf_recommend({"song_name": seed_song_name, "top_k": top_k})
        cf_data = cf_result.get("data", {})
        if not isinstance(cf_data, dict):
            cf_data = {}
        cf_data = cast(dict[str, object], cf_data)
        recommendations = cf_data.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        recommendations = cast(list[object], recommendations)

        if cf_result.get("ok") is not True and not recommendations:
            return {"ok": False, "data": [], "error": cf_result.get("error", "CF recommendation failed")}

        for rec_obj in recommendations:
            if not isinstance(rec_obj, dict):
                continue
            rec = cast(dict[str, object], rec_obj)
            rec_id = str(rec.get("id") or "")
            if not rec_id:
                continue
            cf_items.append({"id": rec_id, "score": _to_float(rec.get("score"), 0.0), "payload": rec})

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
        }

    for row in cf_items:
        item_id = row["id"]
        payload = row["payload"]
        split = _split_name(str(payload.get("name", "")))
        if item_id not in merged:
            merged[item_id] = {
                "id": payload.get("id"),
                "title": split["title"],
                "artist": split["artist"],
                "genre": "",
                "track_id": payload.get("id"),
                "semantic_similarity": None,
                "distance": None,
                "cf_score": payload.get("score"),
                "score": w_cf * cf_norm.get(item_id, 0.0),
                "sources": ["cf"],
            }
        else:
            merged[item_id]["cf_score"] = payload.get("score")
            merged[item_id]["score"] = merged[item_id]["score"] + w_cf * cf_norm.get(item_id, 0.0)
            sources = merged[item_id]["sources"]
            if "cf" not in sources:
                sources.append("cf")

    ranked = sorted(merged.values(), key=lambda row: row["score"], reverse=True)
    return {"ok": True, "data": ranked[:top_k]}
