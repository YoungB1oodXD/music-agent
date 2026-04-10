# AGENTS.md

**Updated:** 2026-04-10  
**Stack:** Python 3.11, FastAPI, Qwen/OpenAI-compatible, ChromaDB, Implicit ALS, React 19, Vite, TailwindCSS v4

## Purpose

This file is for coding agents operating in `E:\Workspace\music_agent`.
Prefer small, pattern-matching changes. Verify with the repo's actual checks.

## High-Level Architecture

Dual-brain music recommendation:
- **Left brain:** semantic retrieval (BGE-M3 + ChromaDB)
- **Right brain:** collaborative filtering (Implicit ALS)
- **Runtime:** intent extraction → slot filling → tool dispatch → response synthesis

## Repository Layout

```
src/
├── agent/        # Orchestration, intent routing
├── api/          # FastAPI app and session endpoints
├── llm/          # Qwen client, prompt schemas
├── rag/          # Retrieval context building
├── tools/        # Tool registry + semantic/CF/hybrid tools
├── manager/      # Session state models
├── recommender/  # Implicit ALS recommender
└── searcher/     # Chroma/BGE semantic search
frontend/         # React + Vite app
scripts/          # Entry-point scripts, training, CLI
tests/            # Standalone smoke/unit scripts (not pytest)
```

## Source-of-Truth Configs

- Backend deps: `requirements.txt`
- Frontend: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`

## Environment Setup

### Backend

```bash
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend && npm install
```

### Required Environment Variables

```bash
# Windows BLAS pinning (before importing implicit)
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OMP_NUM_THREADS=1

# LLM mode
set MUSIC_AGENT_LLM_MODE=mock   # No API key needed
set MUSIC_AGENT_LLM_MODE=qwen   # Requires DashScope key

# Qwen credentials
set DASHSCOPE_API_KEY_BAILIAN=your_key
set DASHSCOPE_API_KEY=your_key
```

## Build / Run Commands

```bash
# Backend API (port 8000)
python scripts/run_api.py

# Frontend dev (port 3000)
cd frontend && npm run dev

# Frontend production build
cd frontend && npm run build
```

## Lint / Typecheck

### Python (no formal linter config)

```bash
python -m compileall src scripts tests
```

### Frontend TypeScript

```bash
cd frontend && npm run lint        # tsc --noEmit
cd frontend && npm run lint && npm run build
```

## Test Commands

**Tests are standalone scripts, NOT pytest.** Run them directly:

```bash
# Core tests
python tests/tool_registry_unit.py
python tests/agent_orchestrator_smoke.py
python tests/api_chat_smoke.py
python tests/api_feedback_refresh_smoke.py
python tests/rag_sanitize_smoke.py
python tests/qwen_live_smoke.py

# Module smoke runners
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py
```

## Data / Model Build Pipeline

```bash
python scripts/data_processor_bge.py
python scripts/build_metadata_from_json.py
python scripts/train_cf.py
python scripts/vectorizer_bge.py
python scripts/build_audio_mapping.py
```

**Do NOT rely on:** `python scripts/run_hybrid_pipeline.py` (broken)

## Python Code Style

### Imports
- stdlib → third-party → local `src.*`
- Prefer absolute imports: `from src.tools.registry import ToolRegistry`
- Avoid wildcard imports
- Newer modules: `from __future__ import annotations`

### Formatting
- 4 spaces
- Preserve UTF-8 headers in Chinese text files
- Match nearby docstring/comment language

### Types
- Add type hints to public functions
- Prefer modern built-in generics
- Use `cast()` after runtime checks, not `as any`
- No `@ts-ignore`, `@ts-expect-error` equivalents

### Naming
- Modules/functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Internal helpers: leading underscore (`_INTENT_*`, `_SLOT_*`)

### Paths and Files
- Prefer `pathlib.Path`
- Derive project-relative paths from `__file__`
- Text reads/writes: `encoding="utf-8"`
- Create dirs: `mkdir(parents=True, exist_ok=True)`

### Error Handling
- Prefer specific exceptions over `except Exception`
- Broad catches: `logger.error(..., exc_info=True)`
- Missing files: raise `FileNotFoundError` or `ImportError`
- API layer: convert to `HTTPException` or structured responses

### Logging
- `logger = logging.getLogger(__name__)`

## Tool-Layer Conventions

Tool handlers return:
```python
{"ok": bool, "data": object, "error": str | None}
```

Schema validation compatible with `src/tools/registry.py`. Do not change tool argument names.

## Frontend Code Style

### Structure
- External imports first, then local
- Match nearby file style (relative vs `@` alias)

### Formatting
- 2 spaces
- Semicolons standard
- Function-component JSX with multiline Tailwind strings

### Types
- `interface` for props and API payloads
- Async service functions: explicit return types
- `Record<string, unknown>` over loose objects
- Avoid `any`; some legacy uses exist

### Naming
- Components/interfaces/types: `PascalCase`
- Functions/variables/hooks: `camelCase`
- Component files: `PascalCase.tsx`

### Error Handling
- Service functions: `throw Error` for HTTP/parse failure
- UI: catch and degrade gracefully
- `console.error` sparingly

## Frontend/Backend Integration

- API base: `/api`
- Vite proxy: `/api` → `http://localhost:8000` (rewrite), `/audio` → no rewrite
- Check `frontend/src/config/api.ts` and `frontend/vite.config.ts` before changing endpoints

## Gotchas

- Mixed Chinese/English strings are intentional
- Windows BLAS env pinning must precede `implicit` import
- Scripts inject repo root into `sys.path` before `src.*` imports
- Backend style mixed: newer orchestration/tooling is stricter than older modules
- Frontend has legacy Gemini/AI Studio residue (`@google/genai`, `GEMINI_API_KEY`); active backend is DashScope/Qwen

## Agent Rules of Thumb

- Prefer minimal fixes over refactors
- Follow existing local patterns before new abstractions
- Verify with direct script execution, not imagined test runners
- Single backend test: `python tests/<name>.py`
- Frontend changes: `npm run lint && npm run build`
