#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import cast


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _add_project_root_to_syspath(project_root: Path) -> None:
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _select_latest_jsonl(sessions_dir: Path) -> Path:
    if not sessions_dir.exists():
        raise ValueError(f"错误：未找到 sessions 目录：{sessions_dir}")
    if not sessions_dir.is_dir():
        raise ValueError(f"错误：sessions 不是目录：{sessions_dir}")

    candidates = list(sessions_dir.glob("*.jsonl"))
    if not candidates:
        raise ValueError(f"错误：未找到任何 transcript 文件（*.jsonl）：{sessions_dir}")

    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return -1.0

    candidates.sort(key=_mtime)
    latest = candidates[-1]
    if _mtime(latest) < 0:
        raise ValueError(f"错误：无法读取最新 transcript 的 mtime：{latest}")
    return latest


def _mock_sha_seed(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return digest[:10]


def _build_mock_registry():
    from src.tools.registry import ToolRegistry

    def semantic_search(args: dict[str, object]) -> dict[str, object]:
        query_text = str(args["query_text"])
        top_k = int(cast(int | float | str, args["top_k"]))

        seed = _mock_sha_seed(query_text)
        catalog: list[tuple[str, str, str, str]] = [
            ("Focus Drift", "Studio Waves", "Ambient", "focus"),
            ("Quiet Pages", "Paper Lanterns", "Lo-fi", "study"),
            ("Caffeine Loop", "Night Library", "Electronic", "work"),
            ("Soft Rain Notes", "Window Seat", "Instrumental", "calm"),
            ("Deep Work", "Mono Tone", "Minimal", "focus"),
            ("Zero Distraction", "No Vocals", "Ambient", "study"),
            ("Warm Lamp", "Evening Desk", "Lo-fi", "study"),
        ]

        data: list[dict[str, object]] = []
        for idx in range(max(1, min(20, top_k))):
            title, artist, genre, tag = catalog[idx % len(catalog)]
            track_id = f"mock_{seed}_{idx + 1:02d}"
            distance = 0.02 * idx
            data.append(
                {
                    "id": f"mock_doc_{track_id}",
                    "title": f"{title} ({tag})",
                    "artist": artist,
                    "genre": genre,
                    "track_id": track_id,
                    "similarity": 1.0 - distance,
                    "distance": distance,
                }
            )

        return {"ok": True, "data": data}

    def cf_recommend(args: dict[str, object]) -> dict[str, object]:
        song_name = str(args["song_name"])
        top_k = int(cast(int | float | str, args["top_k"]))

        seed = _mock_sha_seed(song_name)
        recommendations: list[dict[str, object]] = []
        for idx in range(max(1, min(20, top_k))):
            rec_id = f"mock_cf_{seed}_{idx + 1:02d}"
            recommendations.append(
                {
                    "id": rec_id,
                    "name": f"{song_name} - Similar #{idx + 1}",
                    "score": round(1.0 - 0.03 * idx, 4),
                }
            )

        return {
            "ok": True,
            "data": {
                "matched_song": {"id": f"mock_seed_{seed}", "name": song_name},
                "recommendations": recommendations,
            },
        }

    def hybrid_recommend(args: dict[str, object]) -> dict[str, object]:
        query_text = str(args["query_text"])
        top_k = int(cast(int | float | str, args["top_k"]))
        seed_song_name_obj = args.get("seed_song_name")
        seed_song_name = str(seed_song_name_obj) if seed_song_name_obj is not None else ""

        sem = semantic_search({"query_text": query_text, "top_k": top_k})
        if sem.get("ok") is not True:
            return {"ok": False, "data": [], "error": "mock semantic_search failed"}

        sem_rows_obj = sem.get("data")
        sem_rows: list[object] = []
        if isinstance(sem_rows_obj, list):
            sem_rows = cast(list[object], sem_rows_obj)

        suffix = f" / seed={seed_song_name}" if seed_song_name else ""
        blended: list[dict[str, object]] = []
        for row_obj in sem_rows[: max(1, min(20, top_k))]:
            row: dict[str, object] = cast(dict[str, object], row_obj) if isinstance(row_obj, dict) else {}
            title = str(row.get("title") or "")
            artist = str(row.get("artist") or "")
            track_id = str(row.get("track_id") or "")
            blended.append(
                {
                    "id": f"mock_h_{track_id}",
                    "title": f"{title}{suffix}",
                    "artist": artist,
                    "genre": row.get("genre"),
                    "track_id": track_id,
                    "semantic_similarity": row.get("similarity"),
                    "distance": row.get("distance"),
                    "cf_score": None,
                    "score": row.get("similarity"),
                    "sources": ["semantic", "mock"],
                }
            )
        return {"ok": True, "data": blended}

    semantic_schema: dict[str, object] = {
        "type": "object",
        "properties": {"query_text": {"type": "string"}, "top_k": {"type": "integer"}},
        "required": ["query_text", "top_k"],
    }
    cf_schema: dict[str, object] = {
        "type": "object",
        "properties": {"song_name": {"type": "string"}, "top_k": {"type": "integer"}},
        "required": ["song_name", "top_k"],
    }
    hybrid_schema: dict[str, object] = {
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

    registry = ToolRegistry()
    registry.register(
        name="semantic_search",
        description="(mock) deterministic semantic music search",
        parameters_schema=semantic_schema,
        handler=semantic_search,
    )
    registry.register(
        name="cf_recommend",
        description="(mock) deterministic collaborative recommendation",
        parameters_schema=cf_schema,
        handler=cf_recommend,
    )
    registry.register(
        name="hybrid_recommend",
        description="(mock) deterministic hybrid recommendation",
        parameters_schema=hybrid_schema,
        handler=hybrid_recommend,
    )
    return registry


def _parse_record(line: str, *, path: Path, line_no: int) -> dict[str, object]:
    try:
        parsed_obj = cast(object, json.loads(line))
    except json.JSONDecodeError as exc:
        raise ValueError(f"错误：JSON 解析失败：{path}:{line_no}（{exc.msg}）") from exc

    if not isinstance(parsed_obj, dict):
        raise ValueError(f"错误：JSONL 每行必须是对象：{path}:{line_no}")
    parsed = cast(dict[str, object], parsed_obj)

    required = ("session_id", "model", "user_text", "assistant_text")
    missing = [key for key in required if key not in parsed]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"错误：缺少字段 {joined}：{path}:{line_no}")

    session_id = parsed.get("session_id")
    model = parsed.get("model")
    user_text = parsed.get("user_text")
    assistant_text = parsed.get("assistant_text")

    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError(f"错误：session_id 必须是非空字符串：{path}:{line_no}")
    if not isinstance(model, str):
        raise ValueError(f"错误：model 必须是字符串：{path}:{line_no}")
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError(f"错误：user_text 必须是非空字符串：{path}:{line_no}")
    if not isinstance(assistant_text, str):
        raise ValueError(f"错误：assistant_text 必须是字符串：{path}:{line_no}")

    return parsed


def replay_transcript(path: Path) -> None:
    if not path.exists():
        raise ValueError(f"错误：transcript 文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"错误：transcript 不是文件：{path}")

    from src.agent import MockLLMClient, Orchestrator
    from src.manager.session_state import SessionState

    import src.agent.orchestrator as orchestrator_module

    def _offline_retrieve_semantic_docs(query: str, top_k: int = 5) -> list[dict[str, object]]:
        _ = query
        _ = top_k
        return []

    setattr(orchestrator_module, "retrieve_semantic_docs", _offline_retrieve_semantic_docs)

    mock_registry = _build_mock_registry()
    orchestrator = Orchestrator(llm=MockLLMClient(), tools=mock_registry)

    session_id: str | None = None
    state: SessionState | None = None

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue

            record = _parse_record(line, path=path, line_no=line_no)
            record_session_id = cast(str, record["session_id"])

            if session_id is None:
                session_id = record_session_id
                state = SessionState(
                    session_id=session_id,
                    user_id=None,
                    current_mood=None,
                    current_genre=None,
                    current_scene=None,
                    last_recommendation=None,
                )
            elif record_session_id != session_id:
                raise ValueError(
                    f"错误：同一个 transcript 中 session_id 不一致：{path}:{line_no}（expected={session_id} got={record_session_id}）"
                )

            user_text = cast(str, record["user_text"])
            if state is None:
                raise ValueError(f"错误：无法初始化 SessionState：{path}")
            _ = orchestrator.handle_turn(user_text, state)

    if session_id is None:
        raise ValueError(f"错误：transcript 为空或无有效记录：{path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a transcript JSONL in mock mode")
    group = parser.add_mutually_exclusive_group(required=True)
    _ = group.add_argument("--latest", action="store_true", help="Replay newest data/sessions/*.jsonl")
    _ = group.add_argument("--path", type=str, default=None, help="Replay a specific transcript JSONL")

    class _Args(argparse.Namespace):
        latest: bool = False
        path: str | None = None

    args = cast(_Args, parser.parse_args(argv))

    project_root = _project_root()
    _add_project_root_to_syspath(project_root)

    try:
        if args.path is not None:
            transcript_path = Path(args.path).expanduser().resolve()
        else:
            sessions_dir = project_root / "data" / "sessions"
            transcript_path = _select_latest_jsonl(sessions_dir)

        replay_transcript(transcript_path)
    except Exception as exc:
        detail = str(exc).strip()
        if detail:
            print(f"错误：{detail}", file=sys.stderr)
        else:
            print("错误：replay 失败（未知异常）", file=sys.stderr)
        return 2

    print("replay ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
