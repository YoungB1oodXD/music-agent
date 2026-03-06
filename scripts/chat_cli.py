#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from src.llm.clients.base import BaseLLMClient
    from src.tools.registry import ToolRegistry


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


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _add_project_root_to_syspath(project_root: Path) -> None:
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _write_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        _ = handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _mock_sha_seed(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return digest[:10]


def _build_mock_registry() -> "ToolRegistry":
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


def _build_mock_llm() -> "BaseLLMClient":
    from src.llm.clients.base import BaseLLMClient, ChatResponse
    from typing_extensions import override

    def _as_text(value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        return ""

    def _as_dict(value: object) -> dict[str, object] | None:
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        return None

    def _as_list(value: object) -> list[object] | None:
        if isinstance(value, list):
            return cast(list[object], value)
        return None

    class _CLIMockLLMClient(BaseLLMClient):
        @override
        def chat(
            self,
            messages: list[dict[str, object]],
            tools: list[dict[str, object]] | None = None,
            temperature: float = 0.7,
            max_tokens: int | None = None,
            json_output: bool = False,
            stream: bool = False,
        ) -> ChatResponse:
            _ = tools
            _ = temperature
            _ = max_tokens
            _ = json_output
            _ = stream

            validated = self.validate_messages(messages)
            user_content = self._last_user_message(validated)

            if "INTENT_AND_SLOTS_SCHEMA" in user_content:
                payload = self._extract_payload(user_content)
                user_text = _as_text(payload.get("user_text"))
                data = self._mock_intent_and_slots(user_text)
                content = json.dumps(data, ensure_ascii=False)
                return ChatResponse(content=content, json_data=data, raw={"stage": "intent"})

            if "FINAL_RESPONSE_SCHEMA" in user_content:
                payload = self._extract_payload(user_content)
                data = self._mock_final_response(payload)
                content = json.dumps(data, ensure_ascii=False)
                return ChatResponse(content=content, json_data=data, raw={"stage": "final"})

            fallback: dict[str, object] = {
                "assistant_text": "我在。告诉我你想听什么类型/场景的音乐吧。",
                "recommendations": [],
                "followup_question": "你现在在学习、通勤还是运动？",
            }
            fallback_content = json.dumps(fallback, ensure_ascii=False)
            return ChatResponse(content=fallback_content, json_data=fallback, raw={"stage": "fallback"})

        @staticmethod
        def _last_user_message(messages: list[dict[str, object]]) -> str:
            for message in reversed(messages):
                if _as_text(message.get("role")) == "user":
                    return _as_text(message.get("content"))
            return ""

        @staticmethod
        def _extract_payload(content: str) -> dict[str, object]:
            start = content.find("{")
            if start < 0:
                return {}
            candidate = content[start:]
            try:
                parsed_obj = cast(object, json.loads(candidate))
            except json.JSONDecodeError:
                return {}
            parsed_dict = _as_dict(parsed_obj)
            if parsed_dict is None:
                return {}
            return parsed_dict

        @staticmethod
        def _mock_intent_and_slots(user_text: str) -> dict[str, object]:
            text = user_text.strip()
            lowered = text.lower()

            intent = "search_music"
            if any(token in lowered for token in ("为什么", "理由", "explain")):
                intent = "explain_why"
            elif any(token in lowered for token in ("不喜欢", "跳过", "dislike", "skip", "like", "喜欢")):
                intent = "feedback"
            elif any(token in lowered for token in ("换", "再来", "调整", "refine")):
                intent = "refine_preferences"
            elif any(token in lowered for token in ("推荐", "来点", "听点", "recommend")):
                intent = "recommend_music"

            top_k = 5
            for token in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
                if f"{token}首" in text:
                    try:
                        top_k = max(1, min(20, int(token)))
                    except ValueError:
                        top_k = 5
                    break

            result: dict[str, object] = {"intent": intent, "query_text": text or "推荐音乐", "top_k": top_k}

            if "学习" in text:
                result["scene"] = "学习"
            elif "工作" in text:
                result["scene"] = "工作"
            elif "跑步" in text or "运动" in text or "健身" in text:
                result["scene"] = "运动"
            if "放松" in text:
                result["mood"] = "放松"
            elif "平静" in text:
                result["mood"] = "平静"
            elif "开心" in text:
                result["mood"] = "开心"
            return result

        @staticmethod
        def _mock_final_response(payload: dict[str, object]) -> dict[str, object]:
            recommendations_raw = _as_list(payload.get("recommendations")) or []

            recommendations: list[dict[str, object]] = []
            for item_raw in recommendations_raw:
                item = _as_dict(item_raw)
                if item is None:
                    continue
                rec_id = _as_text(item.get("id"))
                name = _as_text(item.get("name"))
                if not rec_id or not name:
                    continue
                recommendations.append(
                    {
                        "id": rec_id,
                        "name": name,
                        "reason": _as_text(item.get("reason")) or "与当前需求匹配",
                        "citations": _as_list(item.get("citations")) or ["tool_output"],
                    }
                )

            if recommendations:
                lines = [f"我给你整理了 {len(recommendations)} 首可先试听的歌："]
                for idx, rec in enumerate(recommendations[:10], 1):
                    lines.append(f"{idx}. {rec['name']} (id={rec['id']})")
                assistant_text = "\n".join(lines)
            else:
                assistant_text = "我还没有拿到可用的推荐结果，你可以补充一个情绪或场景。"

            return {
                "assistant_text": assistant_text,
                "recommendations": recommendations,
                "followup_question": "你更想要纯音乐、Lo-fi 还是节奏更强一点？",
            }

    return _CLIMockLLMClient()


def _check_qwen_prerequisites() -> None:
    """检查 Qwen 模式运行所需的环境变量和依赖"""
    # API Key 优先级：DASHSCOPE_API_KEY_BAILIAN（百炼普通接口）> DASHSCOPE_API_KEY（Coding Plan）
    bailian_key = os.getenv("DASHSCOPE_API_KEY_BAILIAN", "").strip()
    coding_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not bailian_key and not coding_key:
        raise SystemExit(
            "Missing env var DASHSCOPE_API_KEY_BAILIAN (百炼普通接口，优先) "
            + "or DASHSCOPE_API_KEY (Coding Plan，回退). Set it before using --llm qwen."
        )

    # 检查 openai 依赖
    try:
        import openai
    except ImportError:
        raise SystemExit("Missing dependency: openai. Install with: pip install openai")

    _ = openai


def _qwen_required_artifacts(project_root: Path) -> list[Path]:
    index_path = project_root / "index" / "chroma_bge_m3"
    model_path = project_root / "data" / "models" / "implicit_model.pkl"
    mappings_path = project_root / "data" / "models" / "cf_mappings.pkl"
    return [p for p in (index_path, model_path, mappings_path) if not p.exists()]


def _install_offline_retrieve_semantic_docs() -> None:
    import src.agent.orchestrator as orchestrator_module

    def _offline_retrieve_semantic_docs(query: str, top_k: int = 5) -> list[dict[str, object]]:
        _ = query
        _ = top_k
        return []

    setattr(orchestrator_module, "retrieve_semantic_docs", _offline_retrieve_semantic_docs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Music Agent CLI (chat)")

    _ = parser.add_argument("--llm", choices=["mock", "qwen"], default="mock")
    _ = parser.add_argument("--once", type=str, default=None, help="Single-turn mode")
    _ = parser.add_argument("--session-id", type=str, default=None)

    class _Args(argparse.Namespace):
        llm: str = "mock"
        once: str | None = None
        session_id: str | None = None

    args = cast(_Args, parser.parse_args(argv))

    _ensure_utf8_stdio()

    project_root = _project_root()
    _add_project_root_to_syspath(project_root)

    session_id = (args.session_id or "").strip() or uuid.uuid4().hex
    model = str(args.llm)
    transcript_path = project_root / "data" / "sessions" / f"{session_id}.jsonl"

    print(f"model={model} session_id={session_id}")
    _ = sys.stdout.flush()

    from src.agent.orchestrator import Orchestrator
    from src.manager.session_state import SessionState

    llm: "BaseLLMClient"
    tools: "ToolRegistry"

    if model == "qwen":
        _check_qwen_prerequisites()
        from src.llm.clients.qwen_openai_compat import QwenClient

        llm = QwenClient()
        missing_artifacts = _qwen_required_artifacts(project_root)
        if missing_artifacts:
            _install_offline_retrieve_semantic_docs()
            tools = _build_mock_registry()
            print("[WARN] Local artifacts missing; running qwen with mock tools + empty RAG.")
            for path in missing_artifacts:
                print(f"[WARN] Missing: {path}")
        else:
            from src.tools import build_default_registry

            tools = build_default_registry()
    else:
        _install_offline_retrieve_semantic_docs()
        llm = _build_mock_llm()
        tools = _build_mock_registry()

    orchestrator = Orchestrator(llm=llm, tools=tools)
    state = SessionState(
        session_id=session_id,
        user_id=None,
        llm_status=None,
        current_mood=None,
        current_genre=None,
        current_scene=None,
        last_recommendation=None,
    )

    def run_turn(user_text: str) -> str:
        assistant_text = orchestrator.handle_turn(user_text, state)
        if model == "qwen" and state.llm_status == "fallback":
            print("[WARN] LLM request failed, fallback to local recommendation pipeline.")

        rec_count = len(state.last_recommendation.results) if state.last_recommendation else 0
        print("[SESSION SUMMARY]")
        print(f"llm_status={state.llm_status or 'none'}")
        print(f"recommendation_count={rec_count}")

        _write_jsonl(
            transcript_path,
            {
                "ts": _iso_ts(),
                "session_id": session_id,
                "model": model,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "llm_status": state.llm_status,
            },
        )
        return assistant_text

    if args.once is not None:
        assistant = run_turn(args.once)
        print(assistant)
        return 0

    while True:
        try:
            user_text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0

        text = user_text.strip()
        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            return 0

        assistant = run_turn(user_text)
        print(assistant)


if __name__ == "__main__":
    raise SystemExit(main())
