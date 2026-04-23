#!/usr/bin/env python3
import os
import sys
from typing import cast
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.tools.hybrid_recommend_tool import hybrid_recommend


def _fake_semantic_search(args: dict[str, object]) -> dict[str, object]:
    top_k = int(cast(int | float | str, args.get("top_k", 5)))
    rows: list[dict[str, object]] = [
        {
            "id": "doc_1",
            "track_id": "TR_KEEP_1",
            "title": "Quiet Focus",
            "artist": "Study Crew",
            "genre": "Instrumental",
            "similarity": 0.95,
            "distance": 0.05,
        },
        {
            "id": "doc_2",
            "track_id": "TR_EXCLUDE_1",
            "title": "Should Be Filtered",
            "artist": "Test Artist",
            "genre": "Ambient",
            "similarity": 0.9,
            "distance": 0.1,
        },
    ]
    return {"ok": True, "data": rows[: max(1, min(20, top_k))]}


def run_test() -> None:
    with patch(
        "src.tools.hybrid_recommend_tool.semantic_search", _fake_semantic_search
    ):
        result = hybrid_recommend(
            {
                "query_text": "study music",
                "top_k": 5,
                "exclude_ids": ["TR_EXCLUDE_1"],
            }
        )

        assert result.get("ok") is True
        data_obj = result.get("data")
        assert isinstance(data_obj, list)
        data = cast(list[object], data_obj)

        all_ids: set[str] = set()
        for row_obj in data:
            assert isinstance(row_obj, dict)
            row = cast(dict[str, object], row_obj)
            for key in ("track_id", "id"):
                value = row.get(key)
                if isinstance(value, str) and value:
                    all_ids.add(value)

        assert "TR_EXCLUDE_1" not in all_ids
        assert "TR_KEEP_1" in all_ids

        print("tool_exclude_ids_smoke passed")


if __name__ == "__main__":
    run_test()
