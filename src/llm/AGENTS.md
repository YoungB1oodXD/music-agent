# AGENTS.md — LLM Client Layer

## OVERVIEW

LLM abstraction for Qwen (OpenAI-compatible API). Supports DashScope Bailian and Coding Plan endpoints.

## STRUCTURE

```
llm/
├── clients/
│   ├── base.py              # BaseLLMClient, ChatResponse, ToolCall
│   ├── qwen_openai_compat.py # Qwen client implementation
│   └── __init__.py
├── prompts/
│   ├── schemas.py           # JSON schemas for structured output
│   └── __init__.py
└── __init__.py
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Change API endpoint | `qwen_openai_compat.py` | `DEFAULT_BASE_URL`, env var `DASHSCOPE_BASE_URL` |
| Modify model | `qwen_openai_compat.py` | `DEFAULT_MODEL`, env var `DASHSCOPE_MODEL` |
| Add response schema | `prompts/schemas.py` | Pydantic-compatible JSON schemas |

## ENVIRONMENT VARIABLES

| Variable | Purpose | Priority |
|----------|---------|----------|
| `DASHSCOPE_API_KEY_BAILIAN` | Bailian API key | 1 (highest) |
| `DASHSCOPE_API_KEY` | Coding Plan key | 2 (fallback) |
| `DASHSCOPE_BASE_URL` | Override API URL | Optional |
| `DASHSCOPE_MODEL` | Override model name | Optional |

## CONVENTIONS

- **Client selection**: `MUSIC_AGENT_LLM_MODE=mock` uses `MockLLMClient`
- **Error handling**: Log with `exc_info=True` on API failures
- **Chinese docstrings**: Keep — matches Qwen documentation

## BASE CLASS

```python
class BaseLLMClient:
    def chat(self, messages, tools=None, ...) -> ChatResponse
```