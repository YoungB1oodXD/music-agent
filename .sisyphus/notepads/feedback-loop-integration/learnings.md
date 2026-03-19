# Learnings

## 2026-03-08: Existing Backend Feedback Mechanisms (Reusable)
- `src/manager/session_state.py`: `SessionState.add_feedback()` records `liked_songs` / `disliked_songs`; `exclude_ids` is the shared mechanism for filtering.
- `src/agent/orchestrator.py`:
  - Feedback extraction: `_extract_feedback()` parses `喜欢/不喜欢` + `id:...`.
  - Feedback application: `_apply_feedback()` calls `state.add_feedback(...)`.
  - Refresh detection: `_is_refresh_request()` detects `换一批/再来一批/换批` when intent is `refine_preferences`.
  - Refresh effect: merges previously recommended IDs into `state.exclude_ids` via `_collect_recommended_ids()` + `_merge_ids()`.
  - Tool routing always passes `exclude_ids` into tools via `_build_tool_plan()`.
  - Tools already filter by `exclude_ids`: `src/tools/semantic_search_tool.py`, `src/tools/cf_recommend_tool.py`, `src/tools/hybrid_recommend_tool.py`.
- [Feedback Loop] Updated `Orchestrator._apply_feedback` to add `dislike` and `skip` target IDs to `state.exclude_ids`. This ensures that disliked or skipped items are filtered out in subsequent recommendation or refresh turns. 

## 2026-03-08: Feedback and Refresh Verification
- Verified the feedback loop via `tests/api_feedback_refresh_smoke.py`.
- Acceptance Assertions:
  1. Disliking a specific ID (`不喜欢 id: <id>`) correctly adds it to `state.exclude_ids`.
  2. Refreshing (`换一批`) correctly merges all previously recommended IDs into `state.exclude_ids`.
  3. Subsequent recommendations (after dislike or refresh) do NOT contain any IDs from `state.exclude_ids`.
  4. In mock mode, "换一批" results in a completely different set of recommendations (zero overlap with previous set) because all previous IDs are excluded.

## 2026-03-08: Frontend Feedback Wiring (Conditional Track Update)
- `handleFeedback` in `App.tsx` now uses a conditional update rule for `tracks`:
  - For `换一批` (Refresh): Always replace the current `tracks` with the backend response.
  - For `喜欢/不喜欢` (Like/Dislike):
    - If the backend returns new recommendations (`recommendations.length > 0`), replace the current `tracks`.
    - If the backend returns an empty list (common for feedback turns), keep the existing `tracks`.
    - For `不喜欢` specifically, if the backend returns empty, immediately filter out the disliked track from the current `tracks` using its ID (extracted via regex `/id\s*[:：]\s*(\S+)/`) to provide immediate UI feedback.

## 2026-03-08: Refresh Query Reuse
- Updated `Orchestrator.handle_turn` to reuse the previous recommendation query for refresh requests ("换一批").
- When a refresh request is detected, `query_text` is set to `state.last_recommendation.query` if it exists.
- This ensures that the semantic intent is preserved during refresh, while `exclude_ids` ensures new results are returned.
