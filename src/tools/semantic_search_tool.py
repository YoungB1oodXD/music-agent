from typing import Protocol, cast

from src.searcher.music_searcher import MusicSearcher


SEMANTIC_SEARCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
        "exclude_ids": {"type": "array"},
    },
    "required": ["query_text", "top_k"],
}


_searcher: MusicSearcher | None = None
_SEMANTIC_CANDIDATE_CAP = 40
_SEMANTIC_CANDIDATE_MULTIPLIER = 4
# Recalibrated post-reindex (2026-03-13) to match new similarity distribution.
# Post-reindex top1 for '学习' is ~0.259, 'emo' ~0.295.
_MIN_SEMANTIC_SIMILARITY = 0.26
_HARD_MIN_SEMANTIC_SIMILARITY = 0.18


class _SearcherProtocol(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[dict[str, object]]: ...


def _get_searcher() -> MusicSearcher:
    global _searcher
    if _searcher is None:
        _searcher = MusicSearcher()
    return _searcher


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


def _expand_query_text(query_text: str) -> str:
    """
    Low-risk bilingual query expansion for Chinese scene/mood queries.
    Appends English keywords to improve retrieval in English-heavy metadata.
    """
    expansion_map = {
        ("学习", "复习", "专注"): "study learning focus",
        ("轻音乐", "纯音乐", "器乐"): "instrumental calm ambient",
        ("emo", "难过", "伤心", "安静"): "calm quiet sad",
        ("夜跑", "跑步", "运动", "健身"): "run runner running workout",
        ("高能量", "动感", "燃", "节奏"): "energy energetic upbeat",
        ("夜", "深夜"): "night",
    }

    added_words: list[str] = []
    query_lower = query_text.lower()

    for triggers, expansion in expansion_map.items():
        if any(trigger in query_lower for trigger in triggers):
            for word in expansion.split():
                if word not in query_lower and word not in added_words:
                    added_words.append(word)

    if not added_words:
        return query_text

    # Cap at 12 extra words
    final_expansion = " ".join(added_words[:12])
    return f"{query_text} {final_expansion}".strip()


def _coerce_similarity_to_float(value: object) -> float:
    """
    Safely converts a similarity value to float.
    Treats bool as non-numeric (0.0).
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def semantic_search(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    expanded_query = _expand_query_text(query_text)
    top_k = max(1, int(cast(int | float | str, args["top_k"])))
    candidate_k = min(_SEMANTIC_CANDIDATE_CAP, top_k * _SEMANTIC_CANDIDATE_MULTIPLIER)
    exclude_ids = _parse_exclude_ids(args)

    try:
        searcher = cast(_SearcherProtocol, _get_searcher())
        if expanded_query != query_text:
            results_orig = searcher.search(query_text, top_k=candidate_k)
            results_expanded = searcher.search(expanded_query, top_k=candidate_k)

            merged: dict[str, dict[str, object]] = {}
            for item in results_orig + results_expanded:
                item_ids = _collect_result_ids(item)
                if not item_ids:
                    continue
                key = sorted(list(item_ids))[0]
                if key not in merged:
                    merged[key] = item
                else:
                    existing_sim = _coerce_similarity_to_float(merged[key].get("similarity"))
                    current_sim = _coerce_similarity_to_float(item.get("similarity"))
                    if current_sim > existing_sim:
                        merged[key] = item

            results = sorted(
                merged.values(),
                key=lambda x: _coerce_similarity_to_float(x.get("similarity")),
                reverse=True
            )
        else:
            results = searcher.search(query_text, top_k=candidate_k)
    except FileNotFoundError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except ImportError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "data": [], "error": f"Semantic search failed: {exc}"}

    data: list[dict[str, object]] = []
    for item in results:
        if exclude_ids:
            comparable_ids = _collect_result_ids(item)
            if comparable_ids and comparable_ids.intersection(exclude_ids):
                continue

        data.append(
            {
                "id": cast(object, item.get("id")),
                "title": cast(object, item.get("title")),
                "artist": cast(object, item.get("artist")),
                "genre": cast(object, item.get("genre")),
                "track_id": cast(object, item.get("track_id")),
                "similarity": cast(object, item.get("similarity")),
                "distance": cast(object, item.get("distance")),
            }
        )

    preferred: list[dict[str, object]] = []
    floor_passed: list[dict[str, object]] = []
    for row in data:
        similarity_obj = row.get("similarity")
        if isinstance(similarity_obj, bool):
            continue
        if not isinstance(similarity_obj, (int, float)):
            continue
        similarity = float(similarity_obj)
        if similarity >= _MIN_SEMANTIC_SIMILARITY:
            preferred.append(row)
        elif similarity >= _HARD_MIN_SEMANTIC_SIMILARITY:
            floor_passed.append(row)

    selected: list[dict[str, object]] = preferred[:top_k]
    if len(selected) < top_k:
        for row in floor_passed:
            selected.append(row)
            if len(selected) >= top_k:
                break

    if not selected and data:
        selected = [data[0]]

    return {"ok": True, "data": selected}
