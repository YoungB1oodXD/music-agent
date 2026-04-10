import ast
import logging
from pathlib import Path

from src.searcher.music_searcher import MusicSearcher

logger = logging.getLogger(__name__)

# Heuristic CF weights
_WEIGHT_GENRE = 0.50
_WEIGHT_ARTIST = 0.20
_WEIGHT_DURATION = 0.20
_WEIGHT_TAG = 0.10

# Duration similarity window (seconds)
_DURATION_WINDOW = 30.0

_searcher: MusicSearcher | None = None


def _get_searcher() -> MusicSearcher:
    global _searcher
    if _searcher is None:
        _searcher = MusicSearcher()
    return _searcher


def _parse_tags(tags_str: str) -> set[str]:
    if not tags_str or tags_str == "nan":
        return set()
    try:
        parsed = ast.literal_eval(tags_str)
        if isinstance(parsed, list):
            return {str(t).lower().strip() for t in parsed if t}
    except Exception:
        pass
    return set()


def _duration_similarity(d1: float, d2: float) -> float:
    if d1 <= 0 or d2 <= 0:
        return 0.0
    diff = abs(d1 - d2)
    if diff >= _DURATION_WINDOW:
        return 0.0
    return 1.0 - (diff / _DURATION_WINDOW)


def _score_candidates(
    seed_genre: str,
    seed_artist: str,
    seed_tags: set[str],
    seed_duration: float,
    candidates: list[dict],
) -> list[tuple[float, dict]]:
    scored = []
    for cand in candidates:
        genre = str(cand.get("genre") or "")
        artist = str(cand.get("artist") or "").lower().strip()
        tags_str = str(cand.get("tags") or "")
        duration = float(cand.get("duration") or 0)

        genre_score = (
            1.0 if seed_genre and genre and seed_genre.lower() == genre.lower() else 0.0
        )

        artist_score = 0.0
        if seed_artist and artist:
            seed_artist_norm = seed_artist.lower().strip()
            if seed_artist_norm == artist:
                artist_score = 1.0
            elif seed_artist_norm in artist or artist in seed_artist_norm:
                artist_score = 0.5

        duration_score = _duration_similarity(seed_duration, duration)

        tag_score = 0.0
        if seed_tags:
            cand_tags = _parse_tags(tags_str)
            if cand_tags:
                overlap = len(seed_tags & cand_tags)
                tag_score = min(overlap / max(len(seed_tags), 1), 1.0)

        total = (
            _WEIGHT_GENRE * genre_score
            + _WEIGHT_ARTIST * artist_score
            + _WEIGHT_DURATION * duration_score
            + _WEIGHT_TAG * tag_score
        )

        reasons = []
        if genre_score > 0:
            reasons.append(f"同{seed_genre}流派")
        if artist_score >= 1.0:
            reasons.append("同艺术家")
        elif artist_score >= 0.5:
            reasons.append("相似艺术家")
        if duration_score > 0:
            reasons.append("时长接近")
        if tag_score > 0:
            reasons.append("共同标签")

        cand["_heuristic_score"] = total
        cand["_reason"] = " | ".join(reasons) if reasons else "综合相似"
        scored.append((total, cand))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def heuristic_cf_recommend(song_name: str, top_k: int = 1) -> dict:
    searcher = _get_searcher()

    seed_song = None
    candidates: list[dict] = []

    try:
        seed_results = searcher.search(
            query=song_name,
            top_k=20,
            include_metadata=True,
            include_documents=True,
        )
    except Exception as e:
        logger.warning(f"[HeuristicCF] Seed search failed: {e}")
        return {
            "ok": False,
            "data": {"matched_song": None, "recommendations": []},
            "error": str(e),
        }

    if not seed_results:
        return {
            "ok": False,
            "data": {"matched_song": None, "recommendations": []},
            "error": f"No song found for '{song_name}'",
        }

    seed = seed_results[0]
    seed_id = str(seed.get("track_id") or seed.get("id") or "")
    seed_title = str(seed.get("title") or song_name)
    seed_artist = str(seed.get("artist") or "")
    seed_genre = str(seed.get("genre") or "")
    seed_tags_str = str(seed.get("tags") or "")
    seed_duration = float(seed.get("duration") or 0)
    seed_tags = _parse_tags(seed_tags_str)

    seed_song = {
        "id": seed_id,
        "name": f"{seed_artist} - {seed_title}" if seed_artist else seed_title,
    }

    try:
        broad_results = searcher.search(
            query=f"{seed_genre} {seed_artist}".strip() if seed_genre else seed_artist,
            top_k=top_k * 6,
            include_metadata=True,
            include_documents=False,
        )
    except Exception as e:
        logger.warning(f"[HeuristicCF] Broad search failed: {e}")
        broad_results = []

    for r in broad_results:
        rid = str(r.get("track_id") or r.get("id") or "")
        if rid and rid != seed_id:
            candidates.append(r)

    if len(candidates) < top_k:
        try:
            more_results = searcher.search(
                query=seed_title,
                top_k=top_k * 6,
                include_metadata=True,
                include_documents=False,
            )
            for r in more_results:
                rid = str(r.get("track_id") or r.get("id") or "")
                if (
                    rid
                    and rid != seed_id
                    and rid
                    not in {c.get("track_id") or c.get("id", "") for c in candidates}
                ):
                    candidates.append(r)
        except Exception as e:
            logger.warning(f"[HeuristicCF] Fallback search failed: {e}")

    scored = _score_candidates(
        seed_genre, seed_artist, seed_tags, seed_duration, candidates
    )

    recommendations = []
    for score, cand in scored[:top_k]:
        rid = str(cand.get("track_id") or cand.get("id") or "")
        title = str(cand.get("title") or "")
        artist = str(cand.get("artist") or "")
        genre = str(cand.get("genre") or "")
        is_playable = cand.get("is_playable")
        audio_url = cand.get("audio_url")

        recommendations.append(
            {
                "id": rid,
                "name": f"{artist} - {title}" if artist else title,
                "artist": artist,
                "genre": genre,
                "score": round(score, 3),
                "reason": cand.get("_reason", "综合相似"),
                "is_playable": is_playable,
                "audio_url": audio_url,
            }
        )

    logger.info(
        f"[HeuristicCF] song='{song_name}' -> matched={seed_song['name']}, recs={len(recommendations)}"
    )

    return {
        "ok": True,
        "data": {
            "matched_song": seed_song,
            "recommendations": recommendations,
        },
    }
