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

_HYBRID_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
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
        "id": "fma_4001",
        "track_id": "TR_4001",
        "title": "Study Route",
        "artist": "Lab Band",
        "genre": "Instrumental",
        "similarity": 0.92,
    }
    row_2: dict[str, object] = {
        "id": "fma_4002",
        "track_id": "TR_4002",
        "title": "Run Route",
        "artist": "Lab Band",
        "genre": "Electronic",
        "similarity": 0.89,
    }
    rows: list[dict[str, object]] = [row_1, row_2][:top_k]
    return {"ok": True, "data": rows}


def _hybrid_recommend_handler(args: dict[str, object]) -> dict[str, object]:
    top_k = _to_int(args.get("top_k"), default=5)
    row_1: dict[str, object] = {
        "id": "fma_6001",
        "track_id": "TR_6001",
        "title": "Refined Route",
        "artist": "Hybrid Lab",
        "score": 0.91,
    }
    rows: list[dict[str, object]] = [row_1][:top_k]
    return {"ok": True, "data": rows}


def _fake_retrieve_semantic_docs(
    query_text: str, top_k: int
) -> list[dict[str, object]]:
    _ = query_text
    doc_1: dict[str, object] = {
        "doc_id": 1,
        "artist": "Lab Band",
        "title": "Study Route",
        "genre": "Instrumental",
        "tags": "study, focus",
        "similarity": 0.88,
    }
    doc_2: dict[str, object] = {
        "doc_id": 2,
        "artist": "Lab Band",
        "title": "Run Route",
        "genre": "Electronic",
        "tags": "run, tempo",
        "similarity": 0.86,
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
        name="hybrid_recommend",
        description="Test hybrid recommendation",
        parameters_schema=_HYBRID_SCHEMA,
        handler=_hybrid_recommend_handler,
    )
    return registry


def run_test() -> None:
    setattr(orchestrator_module, "retrieve_semantic_docs", _fake_retrieve_semantic_docs)

    state = SessionState(
        session_id="session_refine_001",
        user_id="user_002",
        current_mood=None,
        current_scene=None,
        current_genre=None,
        last_recommendation=None,
    )
    orchestrator = Orchestrator(llm=MockLLMClient(), tools=build_test_registry())

    first_reply = orchestrator.handle_turn("推荐适合学习时听的歌", state)
    assert bool(first_reply.strip())

    second_reply = orchestrator.handle_turn("换成跑步场景，节奏快一点", state)
    assert bool(second_reply.strip())
    assert state.current_scene is not None

    print("agent_refine_turn passed")


if __name__ == "__main__":
    run_test()
