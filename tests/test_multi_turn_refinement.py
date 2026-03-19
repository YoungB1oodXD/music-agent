import os
import sys
from typing import cast

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import src.agent.orchestrator as orchestrator_module
from src.agent import MockLLMClient, Orchestrator
from src.manager.session_state import SessionState
from src.tools.registry import ToolRegistry

# Mock schemas (simplified)
_SEMANTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "query_text": {"type": "string"},
        "top_k": {"type": "integer"},
        "exclude_ids": {"type": "array", "items": {"type": "string"}},
    },
}

def _semantic_search_handler(args: dict[str, object]) -> dict[str, object]:
    exclude_ids = cast(list[str], args.get("exclude_ids", []))
    top_k = int(cast(int, args.get("top_k", 5)))
    
    # Return some dummy data, but filter out exclude_ids
    all_results = [
        {"id": f"TR_{i}", "track_id": f"TR_{i}", "title": f"Song {i}", "artist": f"Artist {i}"}
        for i in range(1, 21)
    ]
    filtered = [r for r in all_results if r["id"] not in exclude_ids and r["track_id"] not in exclude_ids]
    return {"ok": True, "data": filtered[:top_k]}

def build_test_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        name="semantic_search",
        description="Test semantic search",
        parameters_schema=_SEMANTIC_SCHEMA,
        handler=_semantic_search_handler,
    )
    return registry

def _fake_retrieve_semantic_docs(_query_text: str, _top_k: int) -> list[dict[str, object]]:
    return []

def run_test():
    # Patch retrieve_semantic_docs to avoid actual vector search
    setattr(orchestrator_module, "retrieve_semantic_docs", _fake_retrieve_semantic_docs)
    
    state = SessionState(
        session_id="test_session",
        user_id=None,
        llm_status=None,
        current_mood=None,
        current_scene=None,
        current_genre=None,
        last_recommendation=None
    )
    orchestrator = Orchestrator(llm=MockLLMClient(), tools=build_test_registry())
    
    # Turn 1: 推荐点适合学习的歌
    print("Turn 1: 推荐点适合学习的歌")
    _ = orchestrator.handle_turn("推荐点适合学习的歌", state)
    assert state.last_recommendation is not None
    assert len(state.last_recommendation.results) > 0
    first_results = set(state.last_recommendation.results)
    print(f"  Results: {first_results}")
    
    # Turn 2: 换一批
    print("Turn 2: 换一批")
    _ = orchestrator.handle_turn("换一批", state)
    # Orchestrator._is_refresh_request should trigger and update exclude_ids
    assert len(state.exclude_ids) > 0
    # Ensure previous results are now in exclude_ids
    for rid in first_results:
        assert rid in state.exclude_ids
        
    new_results = set(state.last_recommendation.results)
    print(f"  Exclude IDs: {state.exclude_ids}")
    print(f"  New Results: {new_results}")
    # Ensure no overlap between first turn and second turn
    assert not (first_results & new_results), f"Overlap detected: {first_results & new_results}"
    
    # Turn 3: 不要太吵
    print("Turn 3: 不要太吵")
    _ = orchestrator.handle_turn("不要太吵", state)
    # Orchestrator._extract_energy should catch "不要太吵" -> "low"
    assert state.preference_profile.preferred_energy == "low"
    print(f"  Energy: {state.preference_profile.preferred_energy}")
    
    # Turn 4: 来点纯音乐
    print("Turn 4: 来点纯音乐")
    _ = orchestrator.handle_turn("来点纯音乐", state)
    # Orchestrator._extract_vocals should catch "来点纯音乐" -> "instrumental"
    assert state.preference_profile.preferred_vocals == "instrumental"
    print(f"  Vocals: {state.preference_profile.preferred_vocals}")
    
    print("ok")

if __name__ == "__main__":
    run_test()
