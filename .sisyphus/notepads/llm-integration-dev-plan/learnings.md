# Learnings

Append-only. Capture conventions, patterns, and gotchas discovered while implementing the plan.

- 2026-03-04: Existing repo pattern favors clear runtime errors with install/setup hints (e.g., missing dependency or missing artifact path) and module-level logging with `logging.getLogger(__name__)`.
- 2026-03-04: basedpyright diagnostics in this environment treat some typing patterns strictly; using built-in generics and avoiding `Any` keeps new modules diagnostics-clean.
- 2026-03-04: OpenAI-compatible responses are easiest to process robustly by reading `model_dump()` output and validating expected `choices[0].message` structure before extracting content/tool calls.
- 2026-03-04: `typing.override` is only available in Python 3.12+; for Python 3.11 compatibility use `typing_extensions.override` (or remove the decorator) to avoid import/runtime failures.
- 2026-03-04: Tool wrappers should cache heavy runtime objects (e.g., `MusicSearcher`, `MusicRecommender`) at module scope with lazy initialization to avoid repeated model/index loads per dispatch.
- 2026-03-04: To satisfy basedpyright in script-style tests, use explicit type annotations for variables holding results from dynamic dispatchers (e.g., dict[str, object]) and use typing.cast to narrow object types before indexing or performing operations that require specific types (like string membership checks). 

- In strict basedpyright mode, wrapper outputs typed as dict[str, object] need explicit isinstance narrowing before len() or nested indexing.
- For dict/list invariance, annotate or cast FakeSearcher payloads to dict[str, object] to satisfy declared return types without changing runtime behavior.
- 2026-03-04: For strict basedpyright in smoke tests, narrow dynamic tool payloads with `isinstance` before `len(...)` and nested key access, then `cast` to concrete dict/list shapes.
- 2026-03-04: Returning `list[dict[str, object]]` from fake fixtures may require typed intermediate dict variables to avoid invariance errors on dict literals.
- 2026-03-04: For strict basedpyright loops over dynamic payloads, cast validated lists to `list[object]` before iteration so loop variables are concrete without using `Any`.
- 2026-03-04: When `TypedDict` guarantees a list field (e.g., `sources: list[str]`), index directly instead of `.get(...)` + `isinstance`, which avoids unnecessary-isinstance warnings.
- 2026-03-04: For isolated worktrees, basedpyright may not resolve `src.*` imports from tests; a deterministic smoke test can load a target module by absolute file path via `importlib.util.spec_from_file_location`.
- 2026-03-04: Prompt-injection sanitization can stay deterministic and low-risk by dropping only lines that match blocked case-insensitive substrings while preserving remaining line order.
- 2026-03-04: Enforced RAG context hard cap by tracking cumulative character count and refusing to append the next document line when it would exceed max_chars.
- 2026-03-04: Kept cap behavior deterministic by preserving input order and only truncating when the first candidate line alone is larger than the remaining budget.
- 2026-03-04: For RAG retrievers wrapping tool outputs, keep citation numbering deterministic by enumerating the returned list order (`doc:1..k`) while preserving pass-through metadata fields unchanged.
- 2026-03-04: Orchestrator calls should keep one system message at index 0 and add dialogue history only as user/assistant pairs to satisfy BaseLLMClient validation.
- 2026-03-04: To avoid fabricated recommendation IDs, validate final LLM recommendation IDs against tool-derived seed IDs and drop anything not present in tool outputs.
- 2026-03-04: Agent tests stay offline and artifact-free by monkeypatching `retrieve_semantic_docs` in test scripts while still exercising sanitize/context build flow.

- 2026-03-04: CLI transcripts are JSONL with per-turn fields `ts` (UTC ISO string), `session_id`, `model`, `user_text`, `assistant_text` to keep logging minimal but sufficient for replay/analysis.
- 2026-03-04: Transcript replay stays offline by selecting the latest `data/sessions/*.jsonl`, validating required fields, monkeypatching `src.agent.orchestrator.retrieve_semantic_docs` to return `[]`, and re-running each `user_text` through `Orchestrator.handle_turn` with `MockLLMClient` + deterministic `ToolRegistry`.
  
## Qwen Integration Key Wiring (2026-03-06)  
- Fixed missing `json` import in `tests/qwen_live_smoke.py`.  
- Updated `scripts/chat_cli.py` to support both `DASHSCOPE_MODEL_BAILIAN` (preferred) and `DASHSCOPE_API_KEY` (fallback).  
- Enhanced `tests/dashscope_key_smoke.py` to verify key precedence: explicit > Bailian > Coding.  
- Verified that missing keys result in a clear `EnvironmentError` naming both environment variables.  
"Fixed missing 'import json' in tests/qwen_live_smoke.py which was causing NameError on exception paths." 
- 2026-03-06: Updated scripts/chat_cli.py to accept DASHSCOPE_MODEL_BAILIAN (preferred) or DASHSCOPE_API_KEY (fallback) for Qwen mode, ensuring consistency with the core LLM client's environment variable precedence. 
- 2026-03-06: _check_qwen_prerequisites() now allows either DASHSCOPE_MODEL_BAILIAN (preferred) or DASHSCOPE_API_KEY (fallback) and raises a SystemExit that names both variables and the preference order.
- 2026-03-06: Added observability tags to `src/llm/clients/qwen_openai_compat.py`: `[LLM INIT]` block for client setup, `[LLM SUCCESS]` with latency (ms), and `[LLM ERROR]` with status/response/request_id.
- 2026-03-06: Standardized LLM logging to use multiline blocks with `key=value` pairs for better readability and automated parsing of provider, model, and performance metrics.
- 2026-03-06: Implemented `[SESSION SUMMARY]` in `scripts/chat_cli.py` to print `llm_status` and `recommendation_count` after each turn, providing immediate CLI observability for recommendation performance and LLM health.
