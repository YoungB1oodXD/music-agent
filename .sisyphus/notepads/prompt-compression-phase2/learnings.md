# Learnings - Prompt Compression Phase 2
Append-only log of patterns, conventions, and successful approaches.

- Compressed final-response payload by removing embedded `schema` and replacing raw `intent_slots` with compact `intent` + `slots` (drops duplicated `query_text` and empty values).
- Shortened final-response instruction block into one concise constraint paragraph while preserving hard guards: reuse only provided IDs, evidence-grounded reasons from `rag_context`/`tool_results`, no fabricated metadata.
- Added explicit brevity constraints in prompt (`assistant_text` short, each `reason` <= 1 sentence, each `citations` list 1-2 concrete evidence markers) and reduced `max_tokens` from 600 to 420.
- Capped Phase 2 RAG retrieval at 5 docs in orchestrator (independent from user `top_k`) and reduced retriever passthrough payload to only `artist`, `title`, `genre`, `similarity` for explanation-safe context.
- Shortened context lines to keep stable `[doc:N]` citations while omitting empty fields and using compact `sim=` formatting; dropped verbose fields like `tags`, `distance`, `track_id`, and `id` from RAG context construction.
- Reduced `_TOOL_RESULTS_PROMPT_TOP_K` from 10 to 5 and `_TOOL_RESULTS_PROMPT_MAX_SOURCES` from 5 to 3 to further shrink tool result payloads.
- Refined `_summarize_result_row` to keep only essential fields (`id`, `title`, `artist`, `genre`, `similarity`, `cf_score`, `sources`) and dropped `name` and duplicate `track_id`.
- Minimized `seed_recommendations` in the final response prompt to only `id` and `name`, removing `reason` and `citations` from the candidate list.
- Implemented compact JSON serialization (`separators=(",", ":")`) and omitted empty keys (`tool_failures`, `tool_results`, `rag_context`) in the final payload to save tokens.
- Disabled Qwen "thinking" by default in `QwenClient` to reduce completion tokens and latency. Added support for `DASHSCOPE_ENABLE_THINKING` (true/false) and `DASHSCOPE_THINKING_BUDGET` (int, default 256) via `extra_body` in OpenAI-compatible calls.
