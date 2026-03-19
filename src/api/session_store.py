import uuid
import threading
from src.manager.session_state import SessionState

class SessionStore:
    _lock: threading.Lock

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]:
        with self._lock:
            if session_id and session_id in self._sessions:
                return session_id, self._sessions[session_id]
            
            new_id = session_id if session_id else uuid.uuid4().hex
            new_state = SessionState(
                session_id=new_id,
                user_id=None,
                current_mood=None,
                current_scene=None,
                current_genre=None,
                last_recommendation=None
            )
            self._sessions[new_id] = new_state
            return new_id, new_state

    def reset(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id] = SessionState(
                    session_id=session_id,
                    user_id=None,
                    current_mood=None,
                    current_scene=None,
                    current_genre=None,
                    last_recommendation=None
                )
                return True
            return False
