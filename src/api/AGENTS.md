# AGENTS.md — API Layer
<!-- OMO_INTERNAL_INITIATOR -->

## OVERVIEW
FastAPI application managing chat orchestration, session state, and music discovery endpoints.

## WHERE TO LOOK
- `app.py`: Main entry point. Contains core routes (`/chat`, `/recommend`, `/search`, `/feedback`, `/session`) and middleware setup.
- `sessions.py`: Handles session lifecycle endpoints like reset and status retrieval.
- `session_store.py`: Manages conversation state, intent slots, and history persistence.
- `auth.py`: Implements authentication and authorization logic for protected routes.
- `playlist.py`: Endpoints for creating, updating, and retrieving user-specific playlists.
- `user.py`: Manages user profiles, preferences, and behavioral statistics.

## CONVENTIONS
- **Unified Response**: Tool-layer and API outputs must match `{"ok": bool, "data": object, "error": str | None}`.
- **Intent Routing**: The `/chat` endpoint acts as a proxy to the `Orchestrator` for intent extraction and tool dispatch.
- **Session State**: Use `session_id` to track multi-turn dialogue context.
- **Mocking**: Set `MUSIC_AGENT_LLM_MODE=mock` to bypass LLM API calls during development and testing.
- **TestClient**: Always disable system proxies when running `FastAPI.testclient` to avoid connection issues.
- **Error Handling**: Catch exceptions at the route level and return structured JSON errors instead of raw stack traces.

## KEY PATTERNS
- **Middleware Stack**: CORS, custom logging, and exception handlers are layered in `app.py`.
- **Dependency Injection**: Uses FastAPI `Depends` for `SessionStore` and `Orchestrator` instances.
- **Proxy Handling**: Explicitly disables `http_proxy` and `https_proxy` in `TestClient` to prevent local routing loops.
- **LLM Mode**: Environment-driven switching between `qwen` and `mock` modes for flexible development.

## ANTI-PATTERNS
- **Fat Handlers**: Avoid placing complex logic or model inference directly in `app.py`.
- **Bypassing Orchestrator**: Do not call recommendation tools directly from routes if LLM context is required.
- **Blocking I/O**: Never use synchronous file or network operations inside `async def` handlers.
- **Global State**: Avoid using global variables for session data; use the `SessionStore` dependency.
- **Hardcoded Config**: Don't define ports, timeouts, or model paths locally. Use `src.config`.
