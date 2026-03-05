from typing import Protocol, cast

from src.searcher.music_searcher import MusicSearcher


SEMANTIC_SEARCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
    },
    "required": ["query_text", "top_k"],
}


_searcher: MusicSearcher | None = None


class _SearcherProtocol(Protocol):
    def search(self, query: str, top_k: int = 5) -> list[dict[str, object]]: ...


def _get_searcher() -> MusicSearcher:
    global _searcher
    if _searcher is None:
        _searcher = MusicSearcher()
    return _searcher


def semantic_search(args: dict[str, object]) -> dict[str, object]:
    query_text = str(args["query_text"])
    top_k = int(cast(int | float | str, args["top_k"]))

    try:
        searcher = cast(_SearcherProtocol, _get_searcher())
        results = searcher.search(query_text, top_k=top_k)
    except FileNotFoundError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except ImportError as exc:
        return {"ok": False, "data": [], "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "data": [], "error": f"Semantic search failed: {exc}"}

    data: list[dict[str, object]] = []
    for item in results:
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

    return {"ok": True, "data": data}
