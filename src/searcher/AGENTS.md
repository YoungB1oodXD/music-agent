# AGENTS.md — Searcher (Left Brain / Semantic)
<!-- OMO_INTERNAL_INITIATOR -->

## OVERVIEW
Semantic music search engine using BGE-M3 embeddings and ChromaDB for natural language retrieval.

## WHERE TO LOOK
- `music_searcher.py`: Core `MusicSearcher` class; handles embedding generation and vector queries.
- `index/chroma_bge_m3`: Persistent ChromaDB storage location.
- `scripts/vectorizer_bge.py`: Script for building/updating the vector index.
- `scripts/data_processor_bge.py`: Pre-processing logic for FMA metadata before indexing.

## CONVENTIONS
- **Model**: Use `BAAI/bge-m3` (1024 dimensions). Supports multilingual queries (CN/EN).
- **Storage**: ChromaDB `PersistentClient` at `index/chroma_bge_m3`.
- **Collection**: Default collection name is `music_bge_collection`.
- **Encoding**: Always use `normalize_embeddings=True` during query encoding.
- **Response Format**: Tool-layer handlers must return `{"ok": bool, "data": object, "error": str | None}`.
- **Similarity**: Convert ChromaDB distance to similarity using `1 - distance`.
- **Metadata**: Ensure `title`, `artist`, `genre`, and `track_id` are preserved in the index.

## ANTI-PATTERNS
- **No Online Downloads**: Do not trigger model downloads at runtime; use local cache in `~/.cache/huggingface`.
- **Avoid Re-indexing**: Do not call `vectorizer_bge.py` logic inside the searcher; keep indexing and searching separate.
- **No Raw Distances**: Never expose raw ChromaDB distances to the UI; always use calibrated similarity scores.
- **Sync Blocking**: Avoid long-running blocking calls in the API path; ensure `MusicSearcher` is initialized once.
- **Path Hardcoding**: Do not hardcode absolute paths; derive from `project_root` or use environment variables.
