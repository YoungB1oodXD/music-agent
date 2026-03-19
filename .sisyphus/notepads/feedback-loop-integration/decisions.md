# Decisions

## 2026-03-08: Feedback Loop API Strategy
- Reuse existing `POST /chat` for Like/Dislike/Refresh actions.
- Rationale: Orchestrator already parses feedback tokens (喜欢/不喜欢) and refresh tokens (换一批), and tools already support `exclude_ids`; avoids adding a new endpoint and keeps changes minimal.
- Frontend will send hidden `/chat` messages (not appended to visible chat UI) and update recommendation panel/state locally.
