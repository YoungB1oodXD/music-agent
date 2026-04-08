import logging
from typing import Protocol, cast

logger = logging.getLogger(__name__)

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
_cf_model_ready: bool = False


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

    logger.info(f"[CF] Request: song={song_name}, top_k={top_k}, exclude={len(exclude_ids)}")

    recommendations = []
    matched_song = None

    if _cf_model_ready:
        try:
            logger.info(f"[CF] Using implicit CF model")
            recommender = cast(_RecommenderProtocol, _get_recommender())
            result = recommender.recommend_by_song(song_name, top_k=top_k)
            if result.get("matched_song"):
                matched_song = result["matched_song"]
            raw_recommendations = result.get("recommendations", [])
            for rec_obj in cast(list[object], raw_recommendations):
                if isinstance(rec_obj, dict):
                    rec = cast(dict[str, object], rec_obj)
                    if exclude_ids and _collect_result_ids(rec).intersection(exclude_ids):
                        continue
                    recommendations.append(rec)
            logger.info(f"[CF] Implicit model returned {len(recommendations)} results")
        except Exception as e:
            logger.warning(f"[CF] Implicit model failed: {e}")

    if not recommendations:
        try:
            logger.info(f"[CF] Falling back to ChromaDB semantic similarity")
            from src.searcher.music_searcher import MusicSearcher
            searcher = MusicSearcher()
            search_results = searcher.search(
                query=song_name,
                top_k=top_k * 2,
                include_metadata=True,
                include_documents=False
            )
            for r in search_results:
                tid = str(r.get("track_id") or r.get("id", ""))
                if not tid or tid in exclude_ids:
                    continue
                title = r.get("title", song_name)
                artist = r.get("artist", "")
                rec = {
                    "id": tid,
                    "name": f"{artist} - {title}" if artist else title,
                    "score": r.get("similarity", 0.8),
                }
                recommendations.append(rec)
                if len(recommendations) >= top_k:
                    break
            if search_results and not matched_song:
                first = search_results[0]
                matched_song = {
                    "id": str(first.get("track_id") or first.get("id", "")),
                    "name": f"{first.get('artist', '')} - {first.get('title', song_name)}" if first.get('artist') else first.get('title', song_name)
                }
            logger.info(f"[CF] ChromaDB returned {len(recommendations)} results")
        except ImportError as e:
            logger.warning(f"[CF] ChromaDB not available: {e}")
        except Exception as e:
            logger.warning(f"[CF] ChromaDB search failed: {e}")

    if not recommendations:
        logger.warning(f"[CF] No similar songs found for '{song_name}'")
        return {
            "ok": False,
            "data": {"matched_song": None, "recommendations": []},
            "error": f"No similar songs found for '{song_name}'",
        }

    logger.info(f"[CF] Returning {len(recommendations[:top_k])} recommendations")
    data: dict[str, object] = {
        "matched_song": matched_song,
        "recommendations": recommendations[:top_k],
    }

    return {"ok": True, "data": data}
