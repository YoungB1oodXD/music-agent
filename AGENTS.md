# AGENTS.md

**Generated:** 2026-03-24 | **Updated:** 2026-03-31
**Stack:** Python 3.11 | FastAPI | BGE-M3 | ChromaDB | Implicit ALS | React 19 + Vite + TailwindCSS

## OVERVIEW

Dual-brain music recommendation system with LLM-powered agent orchestration. Left brain: semantic search (BGE-M3 + ChromaDB). Right brain: collaborative filtering (Implicit ALS). Runtime: intent extraction → slot filling → tool dispatch → response synthesis.

## STRUCTURE

```
src/
├── agent/        # Orchestrator — LLM-driven intent/slot extraction, tool dispatch
├── api/          # FastAPI app — /chat, /recommend, /search, /feedback endpoints
├── llm/          # LLM clients — Qwen (OpenAI-compatible), mock client
├── rag/          # Retrieval augmentation — context builder, retriever, sanitizer
├── tools/        # Tool registry — CF/semantic/hybrid recommend tools
├── manager/      # Session state management
├── recommender/  # Collaborative filtering (Right Brain)
└── searcher/     # Semantic search (Left Brain)
frontend/         # React 19 + Vite + TailwindCSS v4
scripts/          # Entry points — training, vectorization, CLI, API server
tests/            # Standalone test scripts (no pytest harness)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new tool | `src/tools/` | Register in `__init__.py` `build_default_registry()`, create handler |
| Modify intent routing | `src/agent/orchestrator.py` | Core dispatch logic, `_ALLOWED_INTENTS` |
| Change LLM provider | `src/llm/clients/` | Base class + Qwen implementation |
| Adjust RAG pipeline | `src/rag/` | Context builder + retriever + sanitizer |
| Add API endpoint | `src/api/app.py` | FastAPI routes, Pydantic models, session store |
| Train models | `scripts/` | train_cf.py, vectorizer_bge.py |
| Frontend component | `frontend/src/components/` | React components with TailwindCSS |
| API service layer | `frontend/src/services/` | TypeScript API client |

## ANTI-PATTERNS (CRITICAL)

- **DO NOT** use `as any`, `@ts-ignore` equivalents in Python or TypeScript
- **DO NOT** suppress type errors — this repo uses type hints
- **DO NOT** delete failing tests to "pass"
- **DO NOT** run `scripts/run_hybrid_pipeline.py` — references missing `cleanup.py`
- **DO NOT** catch broadly without logging: use `except Exception` with `logger.error(..., exc_info=True)`
- **DO NOT** use wildcard imports (`from x import *`)
- **DO NOT** skip BLAS pinning on Windows before importing `implicit`

## UNIQUE STYLES

- **No package structure**: Scripts inject `sys.path.insert(0, repo_root)` before importing `src.*`
- **Encoding headers**: Keep `# -*- coding: utf-8 -*-` for files with non-ASCII content
- **Mixed language**: Chinese/English strings — match nearby code language
- **Mock patterns**: Tests build fake handlers inline, register with `ToolRegistry`
- **BLAS pinning**: Set `OPENBLAS_NUM_THREADS=1` etc. before importing `implicit` on Windows
- **Tool responses**: All handlers return `{"ok": bool, "data": Any, "error": str | None}`

## ENVIRONMENT

```bash
# Install backend dependencies
python -m pip install -r requirements.txt

# Windows BLAS thread pinning (required for implicit)
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OMP_NUM_THREADS=1

# DashScope API keys (priority: BAILIAN > default)
set DASHSCOPE_API_KEY_BAILIAN="your_key"  # Preferred
set DASHSCOPE_API_KEY="your_key"          # Fallback

# LLM mode selection
set MUSIC_AGENT_LLM_MODE=qwen   # Use Qwen (needs API key)
set MUSIC_AGENT_LLM_MODE=mock   # Use mock (no API key needed)

# Install frontend dependencies
cd frontend && npm install
```

## BUILD / TRAIN COMMANDS

No single build tool — "build" generates data artifacts and models.

```bash
# 1. Process data for embedding
python scripts/data_processor_bge.py
# → data/processed/unified_songs_bge.parquet

# 2. Build metadata mapping
python scripts/build_metadata_from_json.py
# → dataset/processed/metadata.json

# 3. Train collaborative filtering model
python scripts/train_cf.py
# → data/models/implicit_model.pkl, cf_mappings.pkl

# 4. Build vector index
python scripts/vectorizer_bge.py
# → index/chroma_bge_m3/

# 5. Build audio mapping
python scripts/build_audio_mapping.py
```

## LINT / TYPECHECK

No linter/formatter configured for Python. For TypeScript:

```bash
# Python minimal sanity check
python -m compileall src scripts tests

# TypeScript type check (frontend)
cd frontend && npm run lint    # tsc --noEmit

# Frontend build
cd frontend && npm run build
```

## TESTS

No pytest harness — tests are standalone scripts with `if __name__ == "__main__"` blocks.

### Run a single test

```bash
python tests/verify_enhancement.py
python tests/tool_registry_unit.py
python tests/agent_orchestrator_smoke.py
python tests/tool_smoke.py
python tests/rag_sanitize_smoke.py
python tests/qwen_live_smoke.py
python tests/api_chat_smoke.py
```

### Run module smoke tests (modules double as test runners)

```bash
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py
```

### Run CLI smoke test

```bash
python scripts/chat_cli.py --llm mock --once "推荐适合学习的歌"
```

### Prerequisites

- `MusicSearcher` requires `index/chroma_bge_m3/`
- `MusicRecommender` requires `data/models/*.pkl` and optionally `dataset/processed/metadata.json`

## CODE STYLE

### Formatting
- Indentation: 4 spaces. Line length: keep readable (<100 preferred).
- Files often have shebang + `# -*- coding: utf-8 -*-` header.
- TypeScript: 2-space indent (Vite default), follow `tsconfig.json`.

### Imports
- Top-level imports, grouped: (1) stdlib, (2) third-party, (3) local.
- Avoid wildcard imports. Use `from __future__ import annotations` for forward refs.

### Types
- Use type hints for public methods and non-trivial helpers.
- Use `Optional[T]`, `Dict[str, Any]`, `cast()` from typing.
- Do NOT use `Any` to silence type errors. Use `cast()` with justification.
- Frontend: Strict TypeScript — no `any`, use proper interfaces in `types.ts`.

### Naming
- Modules: `snake_case.py`. Classes: `PascalCase`. Functions: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`. Internal module constants: `_PREFIXED_NAME`.
- TypeScript: `PascalCase` components, `camelCase` functions/variables.

### Paths
- Use `pathlib.Path`. Compute `project_root` from `__file__`.
- Create parent dirs: `mkdir(parents=True, exist_ok=True)`.

### Logging
- `logger = logging.getLogger(__name__)` at module level.
- Scripts may call `logging.basicConfig()` at import time.
- Log exceptions with `logger.error(..., exc_info=True)`.

### Error Handling
- Missing files: raise `FileNotFoundError` with path.
- Missing deps: raise `ImportError` with install hint.
- Never use bare `except:`. Never swallow errors silently.
- API layer: Convert to `HTTPException` with appropriate status code.

## CLI USAGE

```bash
# Chat CLI (mock mode for testing)
python scripts/chat_cli.py --llm mock

# Chat CLI (Qwen mode)
python scripts/chat_cli.py --llm qwen --once "推荐适合学习的歌"

# Interactive CLI session
python scripts/chat_cli.py --llm mock
> 推荐一些适合学习的歌
> 换一批
> 我想要更欢快的

# API server
python scripts/run_api.py  # Port 8000

# Frontend dev server
cd frontend && npm run dev  # Port 3000, proxies /api and /audio to :8000

# Start all services (PowerShell)
.\start_all.ps1
```

## API ENDPOINTS

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Intelligent conversation — returns recommendations + state |
| POST | `/feedback` | User feedback (like/dislike/refresh) |
| POST | `/reset_session` | Reset session state |
| GET | `/session/{id}` | Get session state summary |
| GET | `/health` | Health check + LLM mode |
| GET | `/health/llm` | LLM connectivity check |
| GET | `/audio/{path}` | Static audio file serving (FMA Small) |

## REPO-SPECIFIC CONVENTIONS

- Mixed Chinese/English: keep user-facing messages consistent with nearby code.
- Some scripts reference missing files — prefer direct scripts: `train_cf.py`, `vectorizer_bge.py`, `data_processor_bge.py`.
- Orchestrator constants use `_PREFIXED` naming (e.g., `_INTENT_RECOMMEND`, `_SLOT_MOOD`).
- Frontend proxies `/api` → `http://localhost:8000` (strips `/api` prefix) and `/audio` → `:8000` (no rewrite).
- Score calibration: display scores clamped to 65-98% range, position-based ranking.
- Demo mode (`_DEMO_MODE_DEFAULT=True`): prioritizes playable songs in results.