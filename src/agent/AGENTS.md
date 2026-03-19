# AGENTS.md — Agent Orchestration Layer

## OVERVIEW

LLM-powered orchestration: intent extraction → slot filling → tool dispatch → response synthesis. Core of the conversational music agent.

## STRUCTURE

```
agent/
├── orchestrator.py   # 1193 lines — main dispatch, intent routing, tool calls
└── mock_llm.py       # Deterministic mock for testing
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new intent | `orchestrator.py` | Add to `_ALLOWED_INTENTS`, handle in `_dispatch_intent` |
| Modify slot extraction | `orchestrator.py` | Slots defined at line 35-50 |
| Adjust RAG integration | `orchestrator.py` | `_RAG_CONTEXT_MAX_CHARS`, `_RAG_RETRIEVAL_TOP_K` |
| Change prompt history | `orchestrator.py` | `_MAX_PROMPT_HISTORY_TURNS` |

## CONVENTIONS

- **Intent constants**: `_INTENT_*` prefix (e.g., `_INTENT_RECOMMEND`)
- **Slot constants**: `_SLOT_*` prefix (e.g., `_SLOT_MOOD`)
- **Config constants**: Module-level with underscore prefix
- **Type casts**: Use `cast()` from typing, not `as`

## DATA FLOW

```
User Input → Intent/Slot Extraction (LLM) → Tool Dispatch → RAG Context → Response Synthesis
```

## KEY INTERFACES

- `Orchestrator` class: Main entry point
- `ToolRegistry`: Dispatch table for tools
- `SessionState`: Conversation state tracking