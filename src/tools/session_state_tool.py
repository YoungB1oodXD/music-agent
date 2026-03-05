from src.manager.session_state import SessionState


_session_state: SessionState | None = None


def _get_session_state() -> SessionState:
    global _session_state
    if _session_state is None:
        _session_state = SessionState(
            session_id="default_session",
            user_id=None,
            current_mood=None,
            current_scene=None,
            current_genre=None,
            last_recommendation=None,
        )
    return _session_state


def update_mood(mood: str) -> dict[str, object]:
    state = _get_session_state()
    state.update_mood(mood)
    return {"ok": True, "data": state.get_context_summary()}


def update_scene(scene: str) -> dict[str, object]:
    state = _get_session_state()
    state.update_scene(scene)
    return {"ok": True, "data": state.get_context_summary()}


def add_feedback(song_id: str, feedback: str) -> dict[str, object]:
    state = _get_session_state()
    state.add_feedback(song_id, feedback)
    return {"ok": True, "data": state.get_context_summary()}


def get_context_summary() -> dict[str, object]:
    state = _get_session_state()
    return {"ok": True, "data": state.get_context_summary()}
