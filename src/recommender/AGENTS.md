# AGENTS.md — Recommender (Content-Based)
<!-- OMO_INTERNAL_INITIATOR -->

## OVERVIEW
Content-based recommendation using semantic search and FMA metadata similarity. No collaborative filtering - relies purely on BGE-M3 embeddings and metadata.

## WHERE TO LOOK
- `src/tools/hybrid_recommend_tool.py`: Hybrid recommendation combining semantic search with metadata-based scoring
- `src/tools/semantic_search_tool.py`: Semantic search using BGE-M3 + ChromaDB

## CONVENTIONS
- **Content-Based Pipeline**:
  1. Semantic search via BGE-M3 embeddings (top_k candidates)
  2. Metadata similarity scoring (genre, mood, energy tags)
  3. Score calibration and filtering
- **Tool Integration**:
  - All public methods must return: `{"ok": bool, "data": object, "error": str | None}`.

## ANTI-PATTERNS
- **Raw Outputs**: Returning model-specific objects or raw floats directly to the API layer.
- **Hardcoded Paths**: Using absolute paths; use project-relative paths.
- **Blocking Calls**: Performing heavy processing inside the request-response cycle.
