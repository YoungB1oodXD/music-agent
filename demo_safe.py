#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, cast


def _ensure_utf8_stdio() -> None:
    try:
        stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
        if callable(stdout_reconfigure):
            _ = stdout_reconfigure(encoding="utf-8")

        stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
        if callable(stderr_reconfigure):
            _ = stderr_reconfigure(encoding="utf-8")
    except Exception:
        pass


PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT_STR = str(PROJECT_ROOT)
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

from src.manager.session_state import SessionState

if TYPE_CHECKING:
    from src.searcher.music_searcher import MusicSearcher


QUERY_1 = "适合深夜独自听的安静的钢琴曲"
QUERY_2 = "适合运动健身的节奏感强的摇滚音乐"
QUERY_3 = "浪漫的法语香颂"


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _normalize_results(raw_results: object) -> list[dict[str, object]]:
    if not isinstance(raw_results, list):
        return []

    normalized: list[dict[str, object]] = []
    items = cast(list[object], raw_results)
    for item in items:
        if not isinstance(item, dict):
            continue
        row = cast(dict[object, object], item)
        artist = str(row.get("artist", "Unknown"))
        title = str(row.get("title", "Unknown"))
        similarity = _coerce_float(row.get("similarity", 0.0))
        normalized.append({"artist": artist, "title": title, "similarity": similarity})
    return normalized


def mock_search(query: str, top_k: int = 3) -> list[dict[str, object]]:
    catalog: dict[str, list[dict[str, object]]] = {
        QUERY_1: [
            {"artist": "Yiruma", "title": "River Flows in You", "similarity": 0.96},
            {"artist": "Ludovico Einaudi", "title": "Nuvole Bianche", "similarity": 0.93},
            {"artist": "Joe Hisaishi", "title": "One Summer's Day", "similarity": 0.9},
        ],
        QUERY_2: [
            {"artist": "The Score", "title": "Unstoppable", "similarity": 0.95},
            {"artist": "Imagine Dragons", "title": "Believer", "similarity": 0.92},
            {"artist": "Fall Out Boy", "title": "Centuries", "similarity": 0.89},
        ],
        QUERY_3: [
            {"artist": "Édith Piaf", "title": "La Vie en rose", "similarity": 0.97},
            {"artist": "Charles Aznavour", "title": "La Bohème", "similarity": 0.94},
            {"artist": "Françoise Hardy", "title": "Tous les garçons et les filles", "similarity": 0.9},
        ],
    }
    fallback: list[dict[str, object]] = [
        {"artist": "Mock Artist A", "title": f"{query} - 推荐 1", "similarity": 0.88},
        {"artist": "Mock Artist B", "title": f"{query} - 推荐 2", "similarity": 0.84},
        {"artist": "Mock Artist C", "title": f"{query} - 推荐 3", "similarity": 0.8},
    ]
    rows: list[dict[str, object]] = catalog.get(query, fallback)
    bounded_k = max(1, min(20, top_k))
    return rows[:bounded_k]


def _load_searcher_if_available(index_dir: Path) -> "MusicSearcher | None":
    if not index_dir.is_dir():
        print("索引目录不存在，跳过 MusicSearcher，使用 mock 搜索。")
        return None

    try:
        from src.searcher.music_searcher import MusicSearcher

        return MusicSearcher()
    except Exception as exc:
        print(f"MusicSearcher 初始化失败，使用 mock 搜索: {exc}")
        return None


def _load_recommender_if_enabled(enabled: bool) -> object | None:
    if not enabled:
        return None
    try:
        from src.recommender.music_recommender import MusicRecommender

        return MusicRecommender()
    except Exception as exc:
        print(f"[CF] 推荐器初始化失败（继续执行）: {exc}")
        return None


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdio()

    parser = argparse.ArgumentParser(description="Music Agent 安全演示")
    _ = parser.add_argument("--cf", action="store_true", help="启用协同过滤（best-effort）")

    class _Args(argparse.Namespace):
        cf: bool = False

    args = cast(_Args, parser.parse_args(argv))

    state = SessionState(
        session_id="safe_demo_001",
        user_id="user_demo",
        current_mood=None,
        current_scene=None,
        current_genre=None,
        last_recommendation=None,
    )

    index_dir = PROJECT_ROOT / "index" / "chroma_bge_m3"
    searcher = _load_searcher_if_available(index_dir)
    recommender = _load_recommender_if_enabled(args.cf)

    queries = [QUERY_1, QUERY_2, QUERY_3]

    for query in queries:
        print(query)

        mood: str | None = state.current_mood
        scene: str | None = state.current_scene
        if query == QUERY_1:
            state.update_mood("安静")
            state.update_scene("深夜")
            mood = "安静"
            scene = "深夜"
        elif query == QUERY_2:
            state.update_scene("运动")
            mood = state.current_mood
            scene = "运动"
        elif query == QUERY_3:
            state.update_scene("浪漫")
            mood = state.current_mood
            scene = "浪漫"

        method = "mock"
        if searcher is not None:
            try:
                results = _normalize_results(searcher.search(query, top_k=3))
                method = "semantic"
            except Exception as exc:
                print(f"语义搜索失败，回退 mock: {exc}")
                results = mock_search(query, top_k=3)
        else:
            results = mock_search(query, top_k=3)

        recommendation_names: list[str] = []
        for row in results:
            artist = str(row.get("artist", "Unknown"))
            title = str(row.get("title", "Unknown"))
            similarity = _coerce_float(row.get("similarity", 0.0))
            print(f"  - {artist} - {title} (相似度: {similarity:.2f})")
            recommendation_names.append(f"{artist} - {title}")

        state.add_dialogue_turn(
            user_input=query,
            system_response=f"为您找到了 {len(recommendation_names)} 首相关音乐。",
            intent="search_music",
            entities={"mood": mood, "scene": scene},
        )
        state.add_recommendation(query=query, results=recommendation_names, method=method)

        if recommender is not None and recommendation_names:
            try:
                recommend_fn = getattr(recommender, "recommend_by_song", None)
                if not callable(recommend_fn):
                    continue
                recommend_by_song = cast(Callable[[str, int], object], recommend_fn)
                cf_payload_obj = recommend_by_song(recommendation_names[0], 2)
                recommendations_obj: object | None = None
                if isinstance(cf_payload_obj, dict):
                    cf_payload = cast(dict[object, object], cf_payload_obj)
                    recommendations_obj = cf_payload.get("recommendations")
                if isinstance(recommendations_obj, list):
                    print("  [CF] 关联推荐:")
                    for item in cast(list[object], recommendations_obj):
                        if not isinstance(item, dict):
                            continue
                        rec = cast(dict[object, object], item)
                        name = str(rec.get("name", "Unknown"))
                        score = _coerce_float(rec.get("score", 0.0))
                        print(f"    * {name} (得分: {score:.2f})")
            except Exception as exc:
                print(f"  [CF] 推荐失败（忽略并继续）: {exc}")

    print(json.dumps(state.get_context_summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
