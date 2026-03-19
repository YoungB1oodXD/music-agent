# Decisions

Append-only. Record decisions and the rationale (what/why), especially anything not explicit in the plan.

- 2026-03-04: Added `src/llm/clients/base.py` with a minimal client contract (`BaseLLMClient`) and structured response models (`ChatResponse`, `ToolCall`) to keep provider-specific code isolated.
- 2026-03-04: Implemented `QwenClient` with lazy OpenAI client initialization so instantiation never triggers network or API key checks; credential validation is deferred to `chat(...)`.
- 2026-03-04: Tool-calling requests always force `stream=False` when `tools` is provided to satisfy DashScope compatibility constraints.
- 2026-03-04: JSON output strategy is instruction-based (`strict JSON` prompt), parsed with `json.loads`, and retried once with `repair JSON only` when initial parsing fails.
- 2026-03-04: Defined two core JSON schemas for LLM interaction:
    - `INTENT_AND_SLOTS_SCHEMA`: Captures user intent (search, recommend, feedback, chat, other) and entities (mood, scene, genre, artist, song_name). Aligns with `SessionState` in `session_state.py`.
    - `FINAL_RESPONSE_SCHEMA`: Structures the final system response with a `reply` (Chinese text), an `action` (search, recommend, chat), and optional `search_params`.
- 2026-03-04: Established system prompt policy: Chinese-first communication, zero-trust for retrieved text, and strict JSON output enforcement when requested.
