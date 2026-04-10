import uuid
import logging
import threading
from src.manager.session_state import SessionState

logger = logging.getLogger(__name__)


def _load_history_to_state(state: SessionState, user_id: str | None = None) -> None:
    from src.database import get_db
    from src.models.chat_history import ChatHistory

    db_gen = get_db()
    db = next(db_gen)
    try:
        query = db.query(ChatHistory).filter(ChatHistory.session_id == state.session_id)
        if user_id is not None:
            query = query.filter(ChatHistory.user_id == user_id)
        rows = query.order_by(ChatHistory.turn_id).all()
        for row in rows:
            state.add_dialogue_turn(
                user_input=str(row.user_input),
                system_response=str(row.system_response),
                intent=str(row.intent) if row.intent else None,
                entities=dict(row.entities) if row.entities else {},
            )
    finally:
        db.close()


class SessionStore:
    _lock: threading.Lock

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._user_sessions: dict[str, list[str]] = {}
        self._history_loaded: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create(
        self, session_id: str | None, user_id: str | None = None
    ) -> tuple[str, SessionState]:
        with self._lock:
            logger.info(f"[SessionStore] get_or_create sid={session_id} uid={user_id}")
            if session_id and session_id in self._sessions:
                state = self._sessions[session_id]
                logger.info(f"[SessionStore] session found, state.uid={state.user_id}")
                if user_id:
                    if state.user_id is None:
                        state.user_id = user_id
                        self._user_sessions.setdefault(user_id, []).append(session_id)
                        logger.info(
                            f"[SessionStore] claimed session {session_id} for uid={user_id}"
                        )
                        return session_id, state
                    if state.user_id == user_id:
                        logger.info(
                            f"[SessionStore] matched uid={user_id}, reusing session"
                        )
                        return session_id, state
                    logger.warning(
                        f"[SessionStore] uid mismatch! state.uid={state.user_id} != uid={user_id}, creating new"
                    )
                else:
                    logger.info(
                        f"[SessionStore] no uid in request, returning existing session"
                    )
                    return session_id, state

            new_id = session_id if session_id else uuid.uuid4().hex
            logger.info(
                f"[SessionStore] creating NEW session {new_id} for uid={user_id}"
            )
            new_state = SessionState(
                session_id=new_id,
                user_id=user_id,
                current_mood=None,
                current_scene=None,
                current_genre=None,
                last_recommendation=None,
            )
            self._sessions[new_id] = new_state
            if user_id:
                self._history_loaded.add((new_id, user_id))
                self._user_sessions.setdefault(user_id, []).append(new_id)
            return new_id, new_state

    def get_by_user(self, user_id: str) -> list[SessionState]:
        with self._lock:
            session_ids = self._user_sessions.get(user_id, [])
            return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    def reset(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                state = self._sessions[session_id]
                if state.user_id and state.user_id in self._user_sessions:
                    self._user_sessions[state.user_id] = [
                        sid
                        for sid in self._user_sessions[state.user_id]
                        if sid != session_id
                    ]
                self._sessions[session_id] = SessionState(
                    session_id=session_id,
                    user_id=None,
                    current_mood=None,
                    current_scene=None,
                    current_genre=None,
                    last_recommendation=None,
                )
                return True
            return False

    def load_history(self, session_id: str, user_id: str | None = None) -> None:
        state = self._sessions.get(session_id)
        if state is None:
            logger.info(f"[SessionStore] load_history: no state for sid={session_id}")
            return
        logger.info(
            f"[SessionStore] load_history: sid={session_id} state.uid={state.user_id} request.uid={user_id}"
        )
        if (
            state.user_id is not None
            and user_id is not None
            and state.user_id != user_id
        ):
            logger.warning(
                f"[SessionStore] load_history: BLOCKED uid mismatch for sid={session_id}"
            )
            return
        effective_user_id = user_id if user_id is not None else state.user_id
        key = (session_id, effective_user_id) if effective_user_id else None
        if key is not None and key in self._history_loaded:
            logger.info(f"[SessionStore] load_history: already loaded key={key}")
            return
        rows_before = len(state.dialogue_history)
        _load_history_to_state(state, user_id)
        rows_after = len(state.dialogue_history)
        logger.info(
            f"[SessionStore] load_history: loaded {rows_after - rows_before} rows, total={rows_after}"
        )
        if key is not None:
            self._history_loaded.add(key)

    def clear_history(self, session_id: str, user_id: str | None = None) -> None:
        from src.database import get_db
        from src.models.chat_history import ChatHistory

        db_gen = get_db()
        db = next(db_gen)
        try:
            query = db.query(ChatHistory).filter(ChatHistory.session_id == session_id)
            if user_id is not None:
                query = query.filter(ChatHistory.user_id == user_id)
            query.delete()
            db.commit()
        finally:
            db.close()
