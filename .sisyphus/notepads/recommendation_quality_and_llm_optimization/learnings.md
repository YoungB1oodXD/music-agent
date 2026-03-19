# Learnings - Recommendation Quality + LLM Optimization
Append-only log of patterns, conventions, and successful approaches.

- The benchmark script `scripts/llm_opt_benchmark.py` can be run with `python scripts/llm_opt_benchmark.py --out <path>`.
- It outputs a JSON artifact containing `chats`, `llm_calls`, `per_chat_summary`, and `citation_stats`.
- `citation_stats` provides aggregated metrics (min, p50, p95, max) for numeric values extracted from recommendation citations.
- Reduced `/chat` LLM usage in `src/agent/orchestrator.py` by making `_extract_intent_and_slots()` deterministic by default (`_ENABLE_LLM_INTENT_EXTRACTION = False`), leaving only the final response generation LLM call on the common path.
- Capped prompt history in `_build_messages()` to the last 5 dialogue turns via `_MAX_PROMPT_HISTORY_TURNS`, which lowers repeated prompt token load.
- Pruned final prompt payload by summarizing `tool_results` through `_summarize_tool_results_for_prompt()` and related helpers: removed tool args/raw blobs, kept only grounding-critical fields (`id`/`track_id`, `name`/`artist`/`title`, numeric scores, `sources`), and limited rows to top 10.
- Reduced RAG prompt budget by calling `build_rag_context(..., max_chars=1200)` via `_RAG_CONTEXT_MAX_CHARS`.
- Verification steps: run `python -m compileall src/agent/orchestrator.py`; then run `python scripts/llm_opt_benchmark.py --out .sisyphus/tmp/llm_opt_benchmark_after_A.json` and confirm `per_chat_summary[].llm_completions == 1` across benchmark queries.
- Semantic/hybrid quality tuning now uses `_MIN_SEMANTIC_SIMILARITY = 0.31` to filter weak semantic candidates before ranking where possible.
- Candidate expansion follows `candidate_k = min(40, top_k * 4)` for semantic retrieval, and hybrid uses the same formula for both semantic and CF internal pools before final merge/slice.
- Fallback behavior keeps best-effort outputs: when thresholded semantic results are insufficient, fill remaining slots with the next-best available candidates in original ranking order instead of returning empty/undersized lists.
- Added a hard semantic floor `_HARD_MIN_SEMANTIC_SIMILARITY = 0.30` in semantic and hybrid paths so normal backfill never introduces sub-0.30 candidates.
- Updated fallback policy: preferred threshold remains `_MIN_SEMANTIC_SIMILARITY = 0.31`, backfill is limited to `[0.30, 0.31)`, and if that still yields none, return a single best available item (if any result exists) instead of empty output.
