# AGENTS.md

**Updated:** 2026-04-01  
**Stack:** Python 3.11, FastAPI, Qwen/OpenAI-compatible client, ChromaDB, Implicit ALS, React 19, Vite, TailwindCSS v4

## Purpose

This file is for coding agents operating in `E:\Workspace\music_agent`.
Prefer small, pattern-matching changes. Verify with the repo’s actual checks instead of inventing new tooling.

## High-Level Architecture

Dual-brain music recommendation system:
- **Left brain:** semantic retrieval with BGE-M3 + ChromaDB
- **Right brain:** collaborative filtering with Implicit ALS
- **Runtime flow:** intent extraction → slot filling → tool dispatch → response synthesis

## Repository Layout

```text
src/
├── agent/        # Orchestration, intent routing, response assembly
├── api/          # FastAPI app and session endpoints
├── llm/          # Qwen client, prompt schemas
├── rag/          # Retrieval context building and sanitization
├── tools/        # Tool registry + semantic/CF/hybrid tools
├── manager/      # Session state models
├── recommender/  # Implicit ALS recommender
└── searcher/     # Chroma/BGE semantic search
frontend/         # React + Vite app
scripts/          # Entry-point scripts, training, audits, CLI, API runner
tests/            # Standalone smoke/unit scripts (not pytest)
```

## Source-of-Truth Config Files

- Backend deps: `requirements.txt`
- Frontend scripts: `frontend/package.json`
- Frontend TS config: `frontend/tsconfig.json`
- Frontend dev/build proxy config: `frontend/vite.config.ts`
- Existing repo docs: `README.md`

## Instruction Files Present / Absent

- Root agent guide exists: `AGENTS.md`
- Additional scoped guides exist under `src/agent/AGENTS.md`, `src/tools/AGENTS.md`, `src/llm/AGENTS.md`, `scripts/AGENTS.md`
- **No** `.cursor/rules/`
- **No** `.cursorrules`
- **No** `.github/copilot-instructions.md`

## Environment Setup

### Backend install

```bash
python -m pip install -r requirements.txt
```

### Frontend install

```bash
cd frontend && npm install
```

### Required / important environment variables

```bash
# Windows BLAS pinning before code that imports implicit
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OMP_NUM_THREADS=1

# LLM mode
set MUSIC_AGENT_LLM_MODE=mock
set MUSIC_AGENT_LLM_MODE=qwen

# Qwen / DashScope credentials
set DASHSCOPE_API_KEY_BAILIAN=your_key
set DASHSCOPE_API_KEY=your_key
```

## Build / Run Commands

### Backend app

```bash
python scripts/run_api.py
```

Starts FastAPI on port `8000`.

### Frontend dev server

```bash
cd frontend && npm run dev
```

Vite runs on port `3000`.

### Frontend production build

```bash
cd frontend && npm run build
```

### Frontend preview

```bash
cd frontend && npm run preview
```

### CLI smoke usage

```bash
python scripts/chat_cli.py --llm mock
python scripts/chat_cli.py --llm qwen --once "推荐适合学习的歌"
```

## Lint / Typecheck / Validation

### Python

There is **no formal Python linter/formatter config** in this repo.
Use the lightweight sanity check below:

```bash
python -m compileall src scripts tests
```

### Frontend TypeScript

```bash
cd frontend && npm run lint
```

Note: `npm run lint` is actually:

```bash
tsc --noEmit
```

### Recommended full validation after frontend changes

```bash
cd frontend && npm run lint && npm run build
```

## Test Commands

### Important: tests are standalone scripts, not pytest

Do **not** assume `pytest`.
To run a single test, execute the target file directly:

```bash
python tests/tool_registry_unit.py
python tests/agent_orchestrator_smoke.py
python tests/api_chat_smoke.py
python tests/api_feedback_refresh_smoke.py
python tests/rag_sanitize_smoke.py
python tests/qwen_live_smoke.py
```

### Module smoke runners

Some source modules are also runnable directly:

```bash
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py
```

### Practical targeted verification

- Tooling change → `python tests/tool_registry_unit.py`
- Orchestrator change → `python tests/agent_orchestrator_smoke.py`
- API change → `python tests/api_chat_smoke.py`
- Feedback/session flow change → `python tests/api_feedback_refresh_smoke.py`
- LLM wiring change → `python tests/qwen_live_smoke.py` or `python tests/dashscope_key_smoke.py`

## Data / Model Build Pipeline

“Build” often means generating artifacts, not compiling code.
Recommended sequence:

```bash
python scripts/data_processor_bge.py
python scripts/build_metadata_from_json.py
python scripts/train_cf.py
python scripts/vectorizer_bge.py
python scripts/build_audio_mapping.py
```

Outputs include processed data, CF model artifacts, and the Chroma index.

## Known Unsafe / Non-Authoritative Commands

Do **not** rely on:

```bash
python scripts/run_hybrid_pipeline.py
```

It references missing pieces and is called out as problematic in repo guidance.

## Python Code Style

### Imports
- Group imports as: stdlib → third-party → local `src.*`
- Prefer absolute project imports like `from src.tools.registry import ToolRegistry`
- Avoid wildcard imports
- Newer typed modules often start with `from __future__ import annotations`

### Formatting
- Use 4 spaces
- Keep lines readable; consistency matters more than rigid wrapping
- Preserve UTF-8 headers in older files containing Chinese text
- Match nearby docstring/comment language

### Types
- Add type hints to public functions and non-trivial helpers
- Prefer modern built-in generics in newer files when consistent with surroundings
- Use `cast()` after runtime checks instead of weakening types
- Do not use typing escapes to silence errors

### Naming
- Modules/functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Internal helper/constants often use a leading underscore, e.g. `_INTENT_*`, `_SLOT_*`

### Paths and files
- Prefer `pathlib.Path`
- Derive project-relative paths from `__file__`
- Use `encoding="utf-8"` for text reads/writes
- Create directories with `mkdir(parents=True, exist_ok=True)`

### Error handling
- Prefer specific exceptions over broad `except Exception`
- If broad catch is necessary, log with context; `logger.error(..., exc_info=True)` is the repo-preferred pattern
- Missing file/resource conditions should raise clear `FileNotFoundError` or `ImportError`
- API layer should convert failures to appropriate `HTTPException` or structured responses

### Logging
- Standard pattern: `logger = logging.getLogger(__name__)`
- Some runtime scripts/modules use `logging.basicConfig()` at import time; do not add extra noisy logging without reason

## Tool-Layer Conventions

- Tool handlers should return the repo envelope:

```python
{"ok": bool, "data": object, "error": str | None}
```

- Keep schema validation behavior compatible with `src/tools/registry.py`
- Do not change tool argument names casually; the orchestrator depends on them

## Frontend Code Style

### Imports and structure
- External imports first, then local imports
- Current frontend mostly uses relative imports even though `@` alias exists
- Match nearby file style instead of forcing alias usage everywhere

### Formatting
- Use 2 spaces
- Semicolons are standard
- JSX is function-component based and often uses multiline Tailwind utility strings

### Types
- Prefer `interface` for props and API payloads
- Give async service functions explicit return types
- Prefer `Record<string, unknown>` over loose object typing when payload shape is uncertain
- Avoid `any`; there are a few legacy uses, but do not spread that pattern

### Naming
- Components/interfaces/types: `PascalCase`
- Functions/variables/hooks: `camelCase`
- Component files usually use `PascalCase.tsx`

### Error handling
- Service functions throw `Error` for HTTP or parse failure
- UI code may catch and degrade gracefully; follow that pattern for user-facing resilience
- Use `console.error` sparingly for real diagnostics

## Frontend/Backend Integration Rules

- Frontend API base is `/api`
- In Vite dev proxy:
  - `/api` → `http://localhost:8000` **with rewrite removing `/api`**
  - `/audio` → `http://localhost:8000` **without rewrite**
- Do not casually change endpoint prefixes without checking `frontend/src/config/api.ts` and `frontend/vite.config.ts`

## Repo-Specific Gotchas

- Mixed Chinese/English strings are intentional; match surrounding code
- Windows BLAS env pinning must happen before importing `implicit`
- Scripts commonly inject repo root into `sys.path` before importing `src.*`
- Backend style is mixed: newer orchestration/tooling code is stricter than older recommender/searcher modules
- Frontend contains legacy Gemini/AI Studio residue (`frontend/README.md`, `@google/genai`, `GEMINI_API_KEY`), but the active repo backend architecture is DashScope/Qwen-based

## Agent Rules of Thumb

- Prefer minimal fixes over refactors
- Follow existing local patterns before introducing new abstractions
- Verify with direct script execution, not imagined test runners
- For a single backend test, run `python tests/<name>.py`
- For frontend changes, default verification is `npm run lint` + `npm run build`
