#!/usr/bin/env python3
from typing import cast


class FakeSearcher:
    def search(self, query_text: str, top_k: int) -> list[dict[str, object]]:
        return [
            {
                "artist": "Miles Davis",
                "title": "So What",
                "similarity": 0.93,
                "query": query_text,
            }
            for _ in range(top_k)
        ]


def semantic_search_tool(searcher: FakeSearcher, query_text: str, top_k: int) -> dict[str, object]:
    return {"ok": True, "data": searcher.search(query_text, top_k)}


def collaborative_filter_tool(song_id: str) -> dict[str, object]:
    return {
        "ok": True,
        "data": {
            "song_id": song_id,
            "recommendations": [
                {"name": "Blue in Green", "score": 0.88},
                {"name": "Freddie Freeloader", "score": 0.81},
            ],
        },
    }


def mood_summary_tool() -> dict[str, object]:
    return {
        "ok": True,
        "data": {
            "current_mood": "calm",
            "confidence": 0.77,
        },
    }


def dispatch_tool(name: str) -> dict[str, object]:
    if name == "semantic_search":
        return {"ok": True, "data": ["semantic_search"]}
    return {"ok": False, "data": []}


def main() -> None:
    searcher = FakeSearcher()

    sem = semantic_search_tool(searcher, "relaxing jazz music", 3)
    assert sem["ok"] is True
    sem_data_obj = sem["data"]
    assert isinstance(sem_data_obj, list)
    sem_data = cast(list[dict[str, object]], sem_data_obj)
    assert len(sem_data) == 3

    cf = collaborative_filter_tool("track-1")
    assert cf["ok"] is True
    cf_data_obj = cf["data"]
    assert isinstance(cf_data_obj, dict)
    cf_data = cast(dict[str, object], cf_data_obj)
    cf_recs_obj = cf_data["recommendations"]
    assert isinstance(cf_recs_obj, list)
    cf_recs = cast(list[dict[str, object]], cf_recs_obj)
    assert len(cf_recs) > 0

    summary = mood_summary_tool()
    assert summary["ok"] is True
    summary_data_obj = summary["data"]
    assert isinstance(summary_data_obj, dict)
    summary_data = cast(dict[str, object], summary_data_obj)
    assert summary_data["current_mood"] == "calm"

    dispatched = dispatch_tool("semantic_search")
    assert dispatched["ok"] is True
    dispatched_data_obj = dispatched["data"]
    assert isinstance(dispatched_data_obj, list)
    dispatched_data = cast(list[object], dispatched_data_obj)
    assert len(dispatched_data) == 1

    print("tool_smoke passed")


if __name__ == "__main__":
    main()
