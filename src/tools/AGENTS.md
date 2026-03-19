# AGENTS.md — Tool Registry Layer

## OVERVIEW

Plugin-style tool dispatch. Tools are registered with JSON schemas and callable handlers. Used by orchestrator for CF/semantic/hybrid recommendations.

## STRUCTURE

```
tools/
├── registry.py              # ToolRegistry class — registration, dispatch, validation
├── cf_recommend_tool.py     # Collaborative filtering tool
├── semantic_search_tool.py  # Semantic search tool
├── hybrid_recommend_tool.py # Hybrid (CF + semantic) tool
├── session_state_tool.py    # Session state access tool
└── __init__.py              # build_default_registry()
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new tool | New file + register in `__init__.py` | Follow existing pattern |
| Modify tool validation | `registry.py` | `_validate_args` method |
| Change dispatch behavior | `registry.py` | `dispatch` method |

## TOOL SPEC

```python
class ToolSpec(TypedDict):
    name: str
    description: str
    parameters_schema: Schema  # JSON Schema
    handler: Callable[[JSON], JSON]
```

## RESPONSE FORMAT

All handlers return:
```python
{"ok": bool, "data": Any, "error": str | None}
```

## CONVENTIONS

- **Schema validation**: Tools validate args against JSON Schema before dispatch
- **Error handling**: Return `{"ok": False, "error": "..."}` on failure
- **Type hints**: Use `JSON = dict[str, object]` alias

## REGISTRATION

```python
registry = ToolRegistry()
registry.register("semantic_search", desc, schema, handler)
```