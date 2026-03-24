# AGENTS.md

**Generated:** 2026-03-24
**Stack:** Python 3.11 | FastAPI | BGE-M3 | ChromaDB | Implicit ALS

## OVERVIEW

Dual-brain music recommendation system with LLM-powered agent orchestration. Left brain: semantic search (BGE-M3 + ChromaDB). Right brain: collaborative filtering (Implicit ALS). Runtime: intent extraction → slot filling → tool dispatch → response synthesis.

## STRUCTURE

```
src/
├── agent/        # Orchestrator — LLM-driven intent/slot extraction, tool dispatch
├── api/          # FastAPI app — /chat, /recommend, /search endpoints
├── llm/          # LLM clients — Qwen (OpenAI-compatible), mock client
├── rag/          # Retrieval augmentation — context builder, retriever, sanitizer
├── tools/        # Tool registry — CF/semantic/hybrid recommend tools
├── manager/      # Session state management
├── recommender/  # Collaborative filtering (Right Brain)
└── searcher/     # Semantic search (Left Brain)
scripts/          # Entry points — training, vectorization, CLI, API server
tests/            # Standalone test scripts (no pytest harness)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new tool | `src/tools/` | Register in `registry.py`, create handler |
| Modify intent routing | `src/agent/orchestrator.py` | Core dispatch logic |
| Change LLM provider | `src/llm/clients/` | Base class + Qwen implementation |
| Adjust RAG pipeline | `src/rag/` | Context builder + retriever |
| Add API endpoint | `src/api/app.py` | FastAPI routes, session store |
| Train models | `scripts/` | train_cf.py, vectorizer_bge.py |

## ANTI-PATTERNS (CRITICAL)

- **DO NOT** use `as any`, `@ts-ignore` equivalents
- **DO NOT** suppress type errors — this repo uses type hints
- **DO NOT** delete failing tests to "pass"
- **DO NOT** run `scripts/run_hybrid_pipeline.py` — references missing `cleanup.py`
- **DO NOT** catch broadly without logging: use `except Exception` with `logger.error(..., exc_info=True)`

## UNIQUE STYLES

- **No package structure**: Scripts inject `sys.path.insert(0, repo_root)` before importing `src.*`
- **Encoding headers**: Keep `# -*- coding: utf-8 -*-` for files with non-ASCII content
- **Mixed language**: Chinese/English strings — match nearby code language
- **Mock patterns**: Tests build fake handlers inline, register with `ToolRegistry`
- **BLAS pinning**: Set `OPENBLAS_NUM_THREADS=1` etc. before importing `implicit` on Windows

## ENVIRONMENT

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Windows BLAS thread pinning (required for implicit)
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1

# DashScope API keys (priority: BAILIAN > default)
export DASHSCOPE_API_KEY_BAILIAN="your_key"  # Preferred
export DASHSCOPE_API_KEY="your_key"          # Fallback
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
```

## LINT / TYPECHECK

No linter/formatter configured. Minimal sanity check:

```bash
python -m compileall src scripts tests
```

## TESTS

No pytest harness — tests are standalone scripts with `if __name__ == "__main__"` blocks.

### Run a single test

```bash
python tests/verify_enhancement.py
python tests/tool_registry_unit.py
python tests/agent_orchestrator_smoke.py
```

### Run module smoke tests

```bash
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py
```

### Prerequisites

- `MusicSearcher` requires `index/chroma_bge_m3/`
- `MusicRecommender` requires `data/models/*.pkl` and optionally `dataset/processed/metadata.json`

## CODE STYLE

### Formatting
- Indentation: 4 spaces. Line length: keep readable (<100 preferred).
- Files often have shebang + `# -*- coding: utf-8 -*-` header.

### Imports
- Top-level imports, grouped: (1) stdlib, (2) third-party, (3) local.
- Avoid wildcard imports.

### Types
- Use type hints for public methods and non-trivial helpers.
- Use `Optional[T]`, `Dict[str, Any]`, `cast()` from typing.
- Do NOT use `Any` to silence type errors.

### Naming
- Modules: `snake_case.py`. Classes: `PascalCase`. Functions: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`. Internal constants: `_PREFIXED_NAME`.

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

## CLI USAGE

```bash
# Chat CLI (mock mode for testing)
python scripts/chat_cli.py --llm mock

# Chat CLI (Qwen mode)
python scripts/chat_cli.py --llm qwen --once "推荐适合学习的歌"

# API server
python scripts/run_api.py  # Port 8000
```

## REPO-SPECIFIC CONVENTIONS

- Mixed Chinese/English: keep user-facing messages consistent with nearby code.
- Some scripts reference missing files — prefer direct scripts: `train_cf.py`, `vectorizer_bge.py`, `data_processor_bge.py`.
- Tool responses follow: `{"ok": bool, "data": Any, "error": str | None}`