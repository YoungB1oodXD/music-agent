from typing import Protocol, cast

from src.recommender.music_recommender import MusicRecommender


CF_RECOMMEND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "song_name": {"type": "string"},
        "top_k": {"type": "integer"},
        "exclude_ids": {"type": "array"},
    },
    "required": ["song_name", "top_k"],
}


_recommender: MusicRecommender | None = None


class _RecommenderProtocol(Protocol):
    def recommend_by_song(self, song_name: str, top_k: int = 5) -> dict[str, object]: ...


def _get_recommender() -> MusicRecommender:
    global _recommender
    if _recommender is None:
        _recommender = MusicRecommender()
    return _recommender


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


def _collect_result_ids(item: dict[str, object]) -> set[str]:
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


def cf_recommend(args: dict[str, object]) -> dict[str, object]:
    song_name = str(args["song_name"])
    top_k = int(cast(int | float | str, args["top_k"]))
    exclude_ids = _parse_exclude_ids(args)

    try:
        recommender = cast(_RecommenderProtocol, _get_recommender())
        result = recommender.recommend_by_song(song_name, top_k=top_k)
    except FileNotFoundError as exc:
        return {"ok": False, "data": {"matched_song": None, "recommendations": []}, "error": str(exc)}
    except Exception as exc:
        return {
            "ok": False,
            "data": {"matched_song": None, "recommendations": []},
            "error": f"Collaborative recommendation failed: {exc}",
        }

    raw_recommendations = result.get("recommendations", [])
    recommendations: list[object] = []
    if isinstance(raw_recommendations, list):
        for rec_obj in cast(list[object], raw_recommendations):
            if not isinstance(rec_obj, dict):
                recommendations.append(rec_obj)
                continue

            rec = cast(dict[str, object], rec_obj)
            if exclude_ids:
                comparable_ids = _collect_result_ids(rec)
                if comparable_ids and comparable_ids.intersection(exclude_ids):
                    continue
            recommendations.append(rec)

    data: dict[str, object] = {
        "matched_song": cast(object, result.get("matched_song")),
        "recommendations": recommendations,
    }

    error = cast(object, result.get("error"))
    if error:
        data["error"] = error
        return {"ok": False, "data": data, "error": error}

    return {"ok": True, "data": data}
