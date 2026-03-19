# Milestone 2: Dialogue State Management Learnings

## Conventions
- **SessionState**: Use `PreferenceProfile` for structured user preferences (energy, vocals, genres).
- **Orchestrator**: Inject structured state summary into the LLM prompt to enable state-aware reasoning.
- **Tools**: Support `exclude_ids` to enable "换一批" (refresh) functionality without repeating recommendations.
- **CLI**: Use `[STATE UPDATE]` and `[SESSION CONTEXT]` prefixes for better observability of the agent's internal state.

## Successful Approaches
- **Mock Mode**: Always verify logic with `--llm mock` to ensure deterministic behavior and offline compatibility.
- **Pydantic Models**: Leverage Pydantic's `model_dump` and `model_validate` for robust state serialization and schema validation.
- **State Change Detection**: Implemented by capturing key fields (mood, scene, genre, energy, vocals, exclude_ids length) before and after `orchestrator.handle_turn` and comparing them to trigger `[STATE UPDATE]` logs.

## Gotchas
- **Windows BLAS**: Keep `OPENBLAS_NUM_THREADS=1` etc. before importing `implicit` to avoid crashes or hangs on Windows.
- **DashScope Constraints**: Remember that DashScope (Qwen) requires the system message at index 0 and doesn't support streaming with tools.
- Enhanced SessionState with exclude_ids and update_preference method for dynamic preference updates.
- Updated summary methods to include exclude_ids for better context tracking.

- Tool exclude filtering compares both `track_id` and `id` (string-normalized) and only removes rows when a comparable id matches.
- Hybrid path propagates `exclude_ids` into semantic/CF calls and re-filters merged rows by both id fields for safety.
- Deterministic refine mappings include `"不要太吵" -> energy=low`, `"来点纯音乐" -> vocals=instrumental`, and `"换一批" -> intent=refine_preferences`.
- Refresh exclusion ids are built by deduping `last_recommendation.results` plus `recommendation_history[*].results`, then merged into `state.exclude_ids` with stable order and a 100-id cap.
- **System Prompt**: Upgraded with explicit rules for "换一批" (refine_preferences), energy (low), and vocals (instrumental) to ensure consistent intent/slot reasoning across different LLM backends.
- **Mock Tool Registry**: Updated mock tool schemas in `scripts/chat_cli.py` to include `exclude_ids` as an optional parameter, ensuring compatibility with the Orchestrator's default behavior and enabling "换一批" testing in mock mode. 
- **Test Coverage**: Added `tests/test_multi_turn_refinement.py` to verify complex multi-turn scenarios including "换一批" (exclusion logic), energy refinement ("不要太吵"), and vocals refinement ("来点纯音乐").
