import os
import sys
from typing import cast

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import src.agent.orchestrator as orchestrator_module
from src.agent import MockLLMClient, Orchestrator
from src.manager.session_state import SessionState
from src.tools.registry import ToolRegistry

_SEMANTIC_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
    },
    "required": ["query_text", "top_k"],
}

_CF_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "song_name": {"type": "string"},
        "top_k": {"type": "integer"},
    },
    "required": ["song_name", "top_k"],
}

_HYBRID_SCHEMA: dict[str, object] = {
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


def _to_int(value: object, default: int = 5) -> int:
    try:
        parsed = int(cast(int | float | str, value))
    except (TypeError, ValueError):
        return default
    return max(1, min(20, parsed))


def _semantic_search_handler(args: dict[str, object]) -> dict[str, object]:
    top_k = _to_int(args.get("top_k"), default=5)
    row_1: dict[str, object] = {
        "id": "fma_1001",
        "track_id": "TR_1001",
        "title": "Quiet Focus",
        "artist": "Study Crew",
        "genre": "Instrumental",
        "similarity": 0.95,
    }
    row_2: dict[str, object] = {
        "id": "fma_1002",
        "track_id": "TR_1002",
        "title": "Soft Notes",
        "artist": "Piano Lab",
        "genre": "Classical",
        "similarity": 0.91,
    }
    row_3: dict[str, object] = {
        "id": "fma_1003",
        "track_id": "TR_1003",
        "title": "Late Night Desk",
        "artist": "Ambient Field",
        "genre": "Ambient",
        "similarity": 0.88,
    }
    rows: list[dict[str, object]] = [row_1, row_2, row_3][:top_k]
    return {"ok": True, "data": rows}


def _cf_recommend_handler(args: dict[str, object]) -> dict[str, object]:
    top_k = _to_int(args.get("top_k"), default=5)
    rec_1: dict[str, object] = {"id": "CF_2001", "name": "Runner - City Flow", "score": 0.96}
    rec_2: dict[str, object] = {"id": "CF_2002", "name": "Pulse - Step Forward", "score": 0.87}
    data: dict[str, object] = {
        "matched_song": {"id": "seed_1", "name": "Seed - Demo Song"},
        "recommendations": [rec_1, rec_2][:top_k],
    }
    return {"ok": True, "data": data}


def _hybrid_recommend_handler(args: dict[str, object]) -> dict[str, object]:
    top_k = _to_int(args.get("top_k"), default=5)
    row_1: dict[str, object] = {
        "id": "fma_3001",
        "track_id": "TR_3001",
        "title": "Hybrid Focus",
        "artist": "Signal Unit",
        "score": 0.93,
    }
    row_2: dict[str, object] = {
        "id": "fma_3002",
        "track_id": "TR_3002",
        "title": "Hybrid Calm",
        "artist": "Signal Unit",
        "score": 0.85,
    }
    rows: list[dict[str, object]] = [row_1, row_2][:top_k]
    return {"ok": True, "data": rows}


def _fake_retrieve_semantic_docs(query_text: str, top_k: int) -> list[dict[str, object]]:
    _ = query_text
    doc_1: dict[str, object] = {
        "doc_id": 1,
        "artist": "Study Crew",
        "title": "Quiet Focus",
        "genre": "Instrumental",
        "tags": "focus, calm",
        "similarity": 0.9,
    }
    doc_2: dict[str, object] = {
        "doc_id": 2,
        "artist": "Piano Lab",
        "title": "Soft Notes",
        "genre": "Classical",
        "tags": "study, piano",
        "similarity": 0.85,
    }
    docs: list[dict[str, object]] = [doc_1, doc_2]
    return docs[: max(1, min(top_k, len(docs)))]


def build_test_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        name="semantic_search",
        description="Test semantic search",
        parameters_schema=_SEMANTIC_SCHEMA,
        handler=_semantic_search_handler,
    )
    registry.register(
        name="cf_recommend",
        description="Test collaborative recommendation",
        parameters_schema=_CF_SCHEMA,
        handler=_cf_recommend_handler,
    )
    registry.register(
        name="hybrid_recommend",
        description="Test hybrid recommendation",
        parameters_schema=_HYBRID_SCHEMA,
        handler=_hybrid_recommend_handler,
    )
    return registry


def run_test() -> None:
    setattr(orchestrator_module, "retrieve_semantic_docs", _fake_retrieve_semantic_docs)

    state = SessionState(
        session_id="session_smoke_001",
        user_id="user_001",
        current_mood=None,
        current_genre=None,
        current_scene=None,
        last_recommendation=None,
    )
    orchestrator = Orchestrator(llm=MockLLMClient(), tools=build_test_registry())

    reply = orchestrator.handle_turn("推荐适合学习时听的轻音乐", state)
    assert isinstance(reply, str)
    assert bool(reply.strip())
    assert len(state.dialogue_history) == 1

    print("agent_orchestrator_smoke passed")


if __name__ == "__main__":
    run_test()
