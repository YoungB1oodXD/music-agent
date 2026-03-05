# AGENTS.md

This repository is a Python-based music recommendation system with two main parts:
- Semantic search (BGE-M3 embeddings + ChromaDB)
- Collaborative filtering (implicit ALS)

The repo is not set up as a packaged library (no `pyproject.toml` / `setup.cfg`).
Most entrypoints are standalone scripts under `scripts/` and runnable modules under `src/`.

Notes for agents:
- `data/`, `dataset/`, and `index/` are gitignored and may be missing locally.
- Many commands will fail unless the required datasets/models/indices exist.
- No dedicated lint/test runner is configured (no pytest/ruff/black config found).
- This repo mixes Chinese/English strings and docstrings; keep user-facing messages consistent with nearby code.

## Environment

- Python: 3.11 (per `README.md` badge)
- Dependencies: `requirements.txt` (pip), optional conda installs mentioned in `README.md`

Install:

```bash
python -m pip install -r requirements.txt
```

Windows / BLAS thread pinning (used in code):
- Some modules set `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.
- Keep these environment settings before importing `implicit` on Windows.

## Build / Train / Run Commands

There is no single build tool; the "build" is generating data artifacts and models.

### Dataset layout (expected)
- Last.fm train JSONs: `dataset/raw/lastfm_train/` (nested subdirs)
- Last.fm subset tags: `dataset/raw/lastfm_subset/` (nested JSONs)
- FMA metadata: `dataset/raw/fma_metadata/` (expects `tracks.csv`)

### Data processing (creates parquet for embedding)

```bash
python scripts/data_processor_bge.py
```

Outputs:
- `data/processed/unified_songs_bge.parquet`

### Build metadata mapping (track_id -> "artist - title")

```bash
python scripts/build_metadata_from_json.py
```

Outputs:
- `dataset/processed/metadata.json`

### Train collaborative filtering model (implicit ALS)

```bash
python scripts/train_cf.py
```

Outputs:
- `data/models/implicit_model.pkl`
- `data/models/cf_mappings.pkl`

### Build vector index (BGE-M3 embeddings -> ChromaDB)

```bash
python scripts/vectorizer_bge.py
```

Outputs:
- `index/chroma_bge_m3/` (ChromaDB persistence)

### Orchestrated pipeline
There is a pipeline driver at `scripts/run_hybrid_pipeline.py`, but it references
`cleanup.py` (missing) and prints some stale names (e.g., "LightFM").
Treat it as experimental unless updated.

## Lint / Typecheck

No linter/formatter/typechecker configuration files were found in this repo.

Recommended minimal "sanity" checks when making changes:

```bash
python -m compileall src scripts tests
```

If you introduce a tool (ruff/black/mypy), do it as a separate, explicit change.

## Tests

There is no pytest/unittest harness detected; tests are mostly runnable scripts.

### Run all available test-like scripts

```bash
python tests/simulate_session.py
python tests/verify_enhancement.py
```

### Run a single test / single check

Use direct execution of the script/module you care about:

```bash
python tests/verify_enhancement.py
```

Or run a single module's built-in smoke test (uses `if __name__ == "__main__"`):

```bash
python src/recommender/music_recommender.py
python src/searcher/music_searcher.py
python scripts/eval_model.py
```

Important: many of these require local artifacts:
- `MusicSearcher` requires `index/chroma_bge_m3/` to exist.
- `MusicRecommender` requires `data/models/*.pkl` and (optionally) `dataset/processed/metadata.json`.

## Code Style Guidelines (follow existing patterns)

### Formatting
- Indentation: 4 spaces.
- Line length: no explicit limit configured; keep it readable (prefer < 100).
- Files commonly include a shebang and `# -*- coding: utf-8 -*-` header.
  Keep the encoding header if the file contains non-ASCII (many docstrings are Chinese).

### Imports
- Use top-level imports.
- Group in this order, separated by blank lines:
  1. Standard library
  2. Third-party libraries
  3. Local imports
- Avoid wildcard imports.

### Types
- Prefer type hints for public methods and non-trivial helpers.
- Use `Optional[T]` and `Dict[str, Any]` as needed; match existing style.
- Do not use `Any` to silence type issues unless the boundary truly is dynamic.

### Naming
- Modules/files: `snake_case.py`.
- Classes: `PascalCase`.
- Functions/methods: `snake_case`.
- Constants: `UPPER_SNAKE_CASE` (see `DEFAULT_MODEL_NAME`, etc.).

### Paths and filesystem
- Prefer `pathlib.Path` and compute `project_root` from `__file__` (common pattern).
- Treat `data/`, `dataset/`, and `index/` as local-only artifacts (gitignored).
- When reading/writing files, create parent directories with `mkdir(parents=True, exist_ok=True)`.

### Logging
- Many modules call `logging.basicConfig(...)` at import time and use `logger = logging.getLogger(__name__)`.
- For libraries, prefer not to reconfigure global logging; for scripts, current pattern is acceptable.
- Log exceptions with stack traces when helpful (e.g., `logger.error(..., exc_info=True)`).

### Error handling
- Prefer explicit exceptions for missing prerequisites:
  - Missing model/index files: raise `FileNotFoundError` with a clear path.
  - Missing optional deps: raise `ImportError` with an install hint.
- Avoid bare `except:`; use `except Exception` if you must catch broadly.
- Do not swallow errors silently; at minimum log debug info.

### Performance / resource constraints
- On Windows, keep BLAS/OMP threads pinned to 1 before importing `implicit`.
- Vectorization can be GPU-intensive and long-running; avoid running it in tight loops.

## Repo-specific conventions / gotchas

- This repo mixes Chinese/English strings and docstrings; keep user-facing messages consistent with nearby code.
- Some scripts have minor inconsistencies (e.g., pipeline references missing files). Prefer the direct scripts:
  `scripts/data_processor_bge.py`, `scripts/vectorizer_bge.py`, `scripts/train_cf.py`.

## Cursor / Copilot rules

- No Cursor rules found: `.cursor/rules/` and `.cursorrules` are not present.
- No Copilot instructions found: `.github/copilot-instructions.md` is not present.
