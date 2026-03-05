from typing import Protocol, cast

from src.recommender.music_recommender import MusicRecommender


CF_RECOMMEND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "song_name": {"type": "string"},
        "top_k": {"type": "integer"},
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


def cf_recommend(args: dict[str, object]) -> dict[str, object]:
    song_name = str(args["song_name"])
    top_k = int(cast(int | float | str, args["top_k"]))

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
        recommendations = cast(list[object], raw_recommendations)

    data: dict[str, object] = {
        "matched_song": cast(object, result.get("matched_song")),
        "recommendations": recommendations,
    }

    error = cast(object, result.get("error"))
    if error:
        data["error"] = error
        return {"ok": False, "data": data, "error": error}

    return {"ok": True, "data": data}
