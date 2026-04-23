# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A conversational music recommendation agent using semantic search and content-based similarity: Left Brain (semantic search via BGE-M3 + ChromaDB) and Right Brain (content-based metadata similarity). The agent uses a LLM orchestrator for intent routing and response synthesis.

## Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (SQLite)
- **Frontend**: React 19, TypeScript, Vite, TailwindCSS, Zustand
- **LLM**: Qwen (OpenAI-compatible API via DashScope)
- **Vector Search**: ChromaDB with BGE-M3 embeddings

## Commands

### Backend
```bash
# Start API server (mock LLM mode by default)
python -m uvicorn src.api.app:app --reload --port 8000

# Start with real LLM
MUSIC_AGENT_LLM_MODE=qwen python -m uvicorn src.api.app:app --reload --port 8000

# Run single test
python -m pytest tests/path/to/test.py -v
```

### Frontend
```bash
cd frontend
npm run dev        # Dev server on port 3000
npm run build      # Production build
npm run lint       # TypeScript check
npm run test:e2e   # Playwright e2e tests
```

## Architecture

```
User → FastAPI (/chat) → Orchestrator → ToolRegistry → [HybridRecommender]
                               ↓                          ↓
                          LLM (Qwen)              Semantic Search
                               ↓                          ↓
                          RAG (ChromaDB)         ChromaDB (BGE-M3)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `src/agent/orchestrator.py` | Intent extraction, slot filling, tool dispatch, response synthesis (~1200 lines) |
| `src/tools/registry.py` | Plugin-style tool dispatch with JSON schema validation |
| `src/llm/clients/qwen_openai_compat.py` | LLM client for DashScope Bailian API |
| `src/searcher/music_searcher.py` | ChromaDB semantic search wrapper |
| `src/rag/retriever.py`, `context_builder.py` | RAG pipeline for LLM context |
| `src/rag/sanitize.py` | Prompt injection prevention |

### Dual-Brain Architecture

- **Left Brain** (`src/searcher/music_searcher.py`): BGE-M3 embeddings + ChromaDB semantic search
- **Right Brain** (`src/tools/hybrid_recommend_tool.py`): Content-based metadata similarity (genre, mood, energy tags)
- **Hybrid** (`src/tools/hybrid_recommend_tool.py`): Blends both streams using weighted scoring

### Intent Routing

LLM intent extraction (`_extract_intent_and_slots`) with deterministic fallback (`_deterministic_intent_slots`). `state.llm_status` marks `live/fallback/live_verified`.

### Query Expansion

Chinese scene/emotion keywords (学习, 跑步) mapped to English search terms (study, run workout) to bridge FMA English metadata gap. See `src/tools/semantic_search_tool.py` `_expand_query_text`.

### Audio Verification

`_get_audio_info` checks file exists and size > 1KB before returning playable URLs. Prevents invalid audio links.

### Data Flow

1. User message → Orchestrator intent/slot extraction (LLM)
2. Intent dispatch → ToolRegistry → hybrid_recommend tool
3. Tool calls semantic search, blends results with metadata scoring
4. RAG context built from semantic search results
5. Response synthesis with LLM + RAG context

### Standard Response Format

All tools/APIs return `{"ok": bool, "data": object, "error": str | None}`. Never return raw model outputs directly.

### LLM Modes

- `MUSIC_AGENT_LLM_MODE=mock` (default): Uses deterministic mock responses for development
- `MUSIC_AGENT_LLM_MODE=qwen`: Uses real DashScope API

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `MUSIC_AGENT_LLM_MODE` | `mock` or `qwen` |
| `DASHSCOPE_API_KEY` / `DASHSCOPE_API_KEY_BAILIAN` | API key for DashScope |
| `DASHSCOPE_BASE_URL` | Override API endpoint |
| `DASHSCOPE_MODEL` | Override model name |
| `LOG_LEVEL` | Logging level (default INFO) |

### Session State

Multi-turn dialogue state tracked via `SessionStore` (in-memory by default). Chat history persisted to SQLite via `ChatHistory` model. Session state includes: current_mood, current_scene, current_genre, preference_profile, liked/disliked tracks, exclude_ids.

### RAG Conventions

- Sanitize all retrieved text with `sanitize_untrusted_text()` before LLM insertion
- Use citation format: `[doc:N] artist=... title=...`
- Context hard limit: 1200 chars (configurable via `src/config.py`)

### Known Issues (from code review)

- CF model removed (2026-04) — system now uses content-based recommendations only
- Global mutable state (`SESSION_STORE`) unsafe with FastAPI multi-worker — use external cache for production
- Token storage in-memory (restart invalidates all sessions)
- Config scattered: display score thresholds defined in both `orchestrator.py` and `src/config.py`
