from .hybrid_recommend_tool import HYBRID_RECOMMEND_SCHEMA, hybrid_recommend
from .registry import ToolRegistry
from .semantic_search_tool import SEMANTIC_SEARCH_SCHEMA, semantic_search
from .session_state_tool import (
    add_feedback,
    get_context_summary,
    update_mood,
    update_scene,
)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        name="semantic_search",
        description="Semantic music search based on query text (PRIMARY TOOL)",
        parameters_schema=SEMANTIC_SEARCH_SCHEMA,
        handler=semantic_search,
    )
    registry.register(
        name="hybrid_recommend",
        description="Content-based hybrid recommendation using semantic search and metadata similarity",
        parameters_schema=HYBRID_RECOMMEND_SCHEMA,
        handler=hybrid_recommend,
    )
    return registry


__all__ = [
    "ToolRegistry",
    "build_default_registry",
    "semantic_search",
    "hybrid_recommend",
    "update_mood",
    "update_scene",
    "add_feedback",
    "get_context_summary",
]
