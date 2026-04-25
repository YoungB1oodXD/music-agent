from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional, cast

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import src.agent.orchestrator as orchestrator_module
from src.agent import MockLLMClient, Orchestrator
from src.api.auth import auth_router, get_current_user
from src.api.playlist import playlist_router, like_router
from src.api.sessions import session_router
from src.models.user_preference import UserPreference
from src.api.session_store import SessionStore
from src.api.user import user_router
from src.database import get_db, init_db
from src.llm.clients import QwenClient
from src.llm.clients.base import ChatResponse
from src.llm.prompts.schemas import (
    FEEDBACK_ADAPTATION_SCHEMA,
    RECOMMENDATION_EXPLANATION_SCHEMA,
)
from src.manager.behavior_recorder import record_behavior, get_behavior_stats
from src.models import ChatHistory, User
from src.tools import build_default_registry
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

LLM_MODE_ENV_VAR = "MUSIC_AGENT_LLM_MODE"

LLM_DEBUG_INFO: dict[str, Any] = {
    "llm_enabled": False,
    "llm_provider": "",
    "llm_model": "",
    "llm_called": False,
    "fallback_used": False,
    "llm_latency_ms": 0,
}


def _mock_sha_seed(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return digest[:10]


def _build_mock_registry() -> ToolRegistry:
    def semantic_search(args: dict[str, object]) -> dict[str, object]:
        query_text = str(args["query_text"])
        top_k = int(cast(int | float | str, args["top_k"]))
        exclude_ids = set(cast(list[str], args.get("exclude_ids") or []))

        seed = _mock_sha_seed(query_text)
        catalog: list[tuple[str, str, str, str]] = [
            ("Focus Drift", "Studio Waves", "Ambient", "focus"),
            ("Quiet Pages", "Paper Lanterns", "Lo-fi", "study"),
            ("Caffeine Loop", "Night Library", "Electronic", "work"),
            ("Soft Rain Notes", "Window Seat", "Instrumental", "calm"),
            ("Deep Work", "Mono Tone", "Minimal", "focus"),
            ("Zero Distraction", "No Vocals", "Ambient", "study"),
            ("Warm Lamp", "Evening Desk", "Lo-fi", "study"),
        ]

        rows: list[dict[str, object]] = []
        for idx in range(40):
            title, artist, genre, tag = catalog[idx % len(catalog)]
            track_id = f"mock_{seed}_{idx + 1:02d}"
            if track_id in exclude_ids:
                continue

            distance = 0.02 * idx
            rows.append(
                {
                    "id": f"mock_doc_{track_id}",
                    "title": f"{title} ({tag})",
                    "artist": artist,
                    "genre": genre,
                    "track_id": track_id,
                    "similarity": 1.0 - distance,
                    "distance": distance,
                }
            )
            if len(rows) >= top_k:
                break

        return {"ok": True, "data": rows}

    def hybrid_recommend(args: dict[str, object]) -> dict[str, object]:
        query_text = str(args["query_text"])
        top_k = int(cast(int | float | str, args["top_k"]))
        exclude_ids = cast(list[str], args.get("exclude_ids") or [])
        seed_song_name_obj = args.get("seed_song_name")
        seed_song_name = (
            str(seed_song_name_obj) if seed_song_name_obj is not None else ""
        )
        intent_obj = args.get("intent")
        intent = str(intent_obj) if intent_obj is not None else "recommend"

        sem = semantic_search(
            {"query_text": query_text, "top_k": top_k, "exclude_ids": exclude_ids}
        )
        if sem.get("ok") is not True:
            return {"ok": False, "data": [], "error": "mock semantic_search failed"}

        sem_rows_obj = sem.get("data")
        sem_rows: list[object] = []
        if isinstance(sem_rows_obj, list):
            sem_rows = cast(list[object], sem_rows_obj)

        sources_label = "semantic" if intent == "search" else "hybrid"
        suffix = f" / seed={seed_song_name}" if seed_song_name else ""
        blended: list[dict[str, object]] = []
        for row_obj in sem_rows[: max(1, min(20, top_k))]:
            row = cast(dict[str, object], row_obj) if isinstance(row_obj, dict) else {}
            title = str(row.get("title") or "")
            artist = str(row.get("artist") or "")
            track_id = str(row.get("track_id") or "")
            blended.append(
                {
                    "id": f"mock_h_{track_id}",
                    "title": f"{title}{suffix}",
                    "artist": artist,
                    "genre": row.get("genre"),
                    "track_id": track_id,
                    "semantic_similarity": row.get("similarity"),
                    "distance": row.get("distance"),
                    "cf_score": None,
                    "score": row.get("similarity"),
                    "sources": [sources_label, "mock"],
                }
            )
        return {"ok": True, "data": blended}

    semantic_schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "query_text": {"type": "string"},
            "top_k": {"type": "integer"},
            "exclude_ids": {"type": "array"},
        },
        "required": ["query_text", "top_k"],
    }
    hybrid_schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "query_text": {"type": "string"},
            "seed_song_name": {"type": "string"},
            "top_k": {"type": "integer"},
            "exclude_ids": {"type": "array"},
            "intent": {"type": "string"},
        },
        "required": ["query_text", "top_k"],
    }

    registry = ToolRegistry()
    registry.register(
        name="semantic_search",
        description="(mock) deterministic semantic music search",
        parameters_schema=semantic_schema,
        handler=semantic_search,
    )
    registry.register(
        name="hybrid_recommend",
        description="(mock) deterministic hybrid recommendation",
        parameters_schema=hybrid_schema,
        handler=hybrid_recommend,
    )
    return registry


def _install_offline_retrieve_semantic_docs() -> None:
    def _offline_retrieve_semantic_docs(
        query: str, top_k: int = 5
    ) -> list[dict[str, object]]:
        _ = query
        _ = top_k
        return []

    setattr(
        orchestrator_module, "retrieve_semantic_docs", _offline_retrieve_semantic_docs
    )


def _get_optional_user(request: Request) -> User | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    from src.api.auth import _get_user_id_from_token
    from src.database import get_db

    db_gen = get_db()
    db = next(db_gen)
    try:
        user_id = _get_user_id_from_token(db, token)
        if user_id is None:
            return None
        return db.query(User).filter(User.id == user_id).first()
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


def _resolve_llm_mode() -> str:
    raw_mode = os.getenv(LLM_MODE_ENV_VAR, "mock").strip().lower()
    if raw_mode in {"mock", "qwen"}:
        return raw_mode
    return "mock"


def _build_runtime() -> tuple[str, SessionStore, ToolRegistry, Orchestrator]:
    llm_mode = _resolve_llm_mode()
    store = SessionStore()

    LLM_DEBUG_INFO["llm_enabled"] = llm_mode == "qwen"
    LLM_DEBUG_INFO["llm_provider"] = "qwen" if llm_mode == "qwen" else "mock"
    LLM_DEBUG_INFO["fallback_used"] = False

    if llm_mode == "qwen":
        tools = build_default_registry()
        llm = QwenClient()
        LLM_DEBUG_INFO["llm_model"] = llm.model
    else:
        _install_offline_retrieve_semantic_docs()
        tools = _build_mock_registry()
        llm = MockLLMClient()
        LLM_DEBUG_INFO["llm_model"] = "mock"

    orchestrator = Orchestrator(llm=llm, tools=tools)
    return llm_mode, store, tools, orchestrator


LLM_MODE, SESSION_STORE, TOOL_REGISTRY, ORCHESTRATOR = _build_runtime()

app = FastAPI(
    title="Music Agent API",
    description="LLM mode is controlled by MUSIC_AGENT_LLM_MODE (mock by default, qwen optional).",
)


# ── Global exception handlers ────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: str | None = None


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Re-serialize HTTPException as a consistent JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": exc.detail, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — prevents raw 500 stack traces leaking."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "Internal server error",
            "detail": None,
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response


FMA_SMALL_AUDIO_DIR = (
    Path(__file__).parent.parent.parent / "dataset" / "raw" / "fma_small"
)
if FMA_SMALL_AUDIO_DIR.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/audio", StaticFiles(directory=str(FMA_SMALL_AUDIO_DIR)), name="audio")

app.include_router(auth_router)
app.include_router(playlist_router)
app.include_router(like_router)
app.include_router(session_router)
app.include_router(user_router)

init_db()


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)


class ChatStateResponse(BaseModel):
    mood: str | None = None
    scene: str | None = None
    genre: str | None = None
    preferred_energy: str | None = None
    preferred_vocals: str | None = None


class HealthVerboseResponse(BaseModel):
    status: str
    llm_mode: str
    components: dict[str, Any]


class RecommendationObject(BaseModel):
    id: str
    name: str
    reason: str | None = None
    citations: list[str] = Field(default_factory=list)
    is_playable: bool | None = None
    audio_url: str | None = None
    score: float | None = None
    display_score: int | None = None
    tags: list[str] = Field(default_factory=list)
    mood_tags: list[str] = Field(default_factory=list)
    scene_tags: list[str] = Field(default_factory=list)
    instrumentation: list[str] = Field(default_factory=list)
    genre: str | None = None
    style: str | None = None
    genre_description: str | None = None


class DebugInfo(BaseModel):
    llm_enabled: bool = False
    llm_provider: str = ""
    llm_model: str = ""
    llm_called: bool = False
    fallback_used: bool = False
    llm_latency_ms: int = 0


class ChatResponseModel(BaseModel):
    session_id: str
    assistant_text: str
    recommendations: list[RecommendationObject]
    recommendation_action: str = Field(
        default="replace", pattern="^(replace|preserve)$"
    )
    state: ChatStateResponse
    debug: DebugInfo = Field(default_factory=DebugInfo)


class ResetSessionRequest(BaseModel):
    session_id: str


class ResetSessionResponse(BaseModel):
    ok: bool


class SessionResponseModel(BaseModel):
    ok: bool
    session_id: str
    state: dict[str, object]


class HealthResponse(BaseModel):
    status: str
    llm_mode: str


class FeedbackRequest(BaseModel):
    session_id: str
    feedback_type: str = Field(..., pattern="^(like|dislike|refresh)$")
    track_id: str | None = None
    track_metadata: dict[str, Any] = Field(default_factory=dict)
    recommendation_context: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    success: bool
    ack_message: str = ""
    updated_preference_state: dict[str, Any] = Field(default_factory=dict)
    next_strategy: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[RecommendationObject] = Field(default_factory=list)
    debug: DebugInfo = Field(default_factory=DebugInfo)


class RefreshRequest(BaseModel):
    session_id: str


class RefreshResponse(BaseModel):
    session_id: str
    recommendations: list[RecommendationObject]
    state: ChatStateResponse
    debug: DebugInfo


class LLMHealthResponse(BaseModel):
    status: str
    llm_mode: str
    llm_provider: str
    llm_model: str
    llm_available: bool
    latency_ms: int | None = None
    error: str | None = None


@app.post("/chat", response_model=ChatResponseModel)
def chat(payload: ChatRequest, request: Request) -> ChatResponseModel:
    global LLM_DEBUG_INFO
    LLM_DEBUG_INFO = {
        "llm_enabled": LLM_MODE == "qwen",
        "llm_provider": "qwen" if LLM_MODE == "qwen" else "mock",
        "llm_model": ORCHESTRATOR.llm.model
        if hasattr(ORCHESTRATOR.llm, "model")
        else "mock",
        "llm_called": False,
        "fallback_used": False,
        "llm_latency_ms": 0,
    }

    current_user = _get_optional_user(request)
    user_id = str(current_user.id) if current_user else None
    session_id, state = SESSION_STORE.get_or_create(payload.session_id, user_id=user_id)

    SESSION_STORE.load_history(session_id, user_id)
    prev_turn_count = len(state.dialogue_history)

    start_time = time.perf_counter()
    turn_result = ORCHESTRATOR.handle_turn(payload.message, state)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if isinstance(turn_result, dict):
        assistant_text = str(turn_result.get("assistant_text", ""))
        recommendations = turn_result.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []
        recommendation_action = str(turn_result.get("recommendation_action", "replace"))
        if recommendation_action not in {"replace", "preserve"}:
            recommendation_action = "replace"

        flat_recommendations: list[dict[str, Any]] = []
        for rec in recommendations:
            rec = dict(rec)
            evidence = rec.get("evidence")
            if isinstance(evidence, dict):
                if rec.get("genre") is None:
                    rec["genre"] = evidence.get("genre")
                if rec.get("genre_description") is None:
                    rec["genre_description"] = evidence.get("genre_description")
                if not rec.get("tags"):
                    rec["tags"] = []
                if isinstance(evidence.get("mood_tags"), list):
                    rec["tags"] = rec["tags"] + evidence["mood_tags"]
                if isinstance(evidence.get("scene_tags"), list):
                    rec["tags"] = rec["tags"] + evidence["scene_tags"]
                if isinstance(evidence.get("instrumentation"), list):
                    rec["tags"] = rec["tags"] + evidence["instrumentation"]
                if evidence.get("energy_note"):
                    rec["tags"] = rec["tags"] + [evidence["energy_note"]]
                rec["tags"] = list(dict.fromkeys(rec["tags"]))
            flat_recommendations.append(rec)
        recommendations = flat_recommendations
    else:
        assistant_text = str(turn_result)
        recommendations = []
        recommendation_action = "replace"

    logger.info(
        f"[CHAT] session={session_id}, latency={latency_ms}ms, "
        f"llm_status={state.llm_status}, recs={len(recommendations)}"
    )

    LLM_DEBUG_INFO["llm_called"] = state.llm_status in ("live", "live_verified")
    LLM_DEBUG_INFO["fallback_used"] = state.llm_status == "fallback"
    LLM_DEBUG_INFO["llm_latency_ms"] = latency_ms

    new_turns = state.dialogue_history[prev_turn_count:]
    if new_turns:
        db_gen = get_db()
        db = next(db_gen)
        try:
            ChatHistory.save_turns(
                db,
                session_id,
                user_id,
                [
                    {
                        "turn_id": turn.turn_id,
                        "user_input": turn.user_input,
                        "system_response": turn.system_response,
                        "intent": turn.intent,
                        "entities": turn.entities,
                        "recommendations": recommendations
                        if idx == len(new_turns) - 1
                        else [],
                    }
                    for idx, turn in enumerate(new_turns)
                ],
            )
        finally:
            db.close()

    SESSION_STORE.save_state(session_id)

    return ChatResponseModel(
        session_id=session_id,
        assistant_text=assistant_text,
        recommendations=recommendations,
        recommendation_action=recommendation_action,
        state=ChatStateResponse(
            mood=state.current_mood,
            scene=state.current_scene,
            genre=state.current_genre,
            preferred_energy=state.preference_profile.preferred_energy,
            preferred_vocals=state.preference_profile.preferred_vocals,
        ),
        debug=DebugInfo(**LLM_DEBUG_INFO),
    )


@app.post("/reset_session", response_model=ResetSessionResponse)
def reset_session(
    payload: ResetSessionRequest,
    current_user: User = Depends(get_current_user),
) -> ResetSessionResponse:
    state = SESSION_STORE.get(payload.session_id)
    if (
        state is not None
        and state.user_id is not None
        and state.user_id != str(current_user.id)
    ):
        raise HTTPException(status_code=403, detail="Not your session")
    SESSION_STORE.clear_history(payload.session_id, str(current_user.id))
    return ResetSessionResponse(ok=SESSION_STORE.reset(payload.session_id))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", llm_mode=LLM_MODE)


@app.get("/health/llm", response_model=LLMHealthResponse)
def health_llm() -> LLMHealthResponse:
    if LLM_MODE != "qwen":
        return LLMHealthResponse(
            status="mock",
            llm_mode=LLM_MODE,
            llm_provider="mock",
            llm_model="mock",
            llm_available=True,
            latency_ms=0,
            error=None,
        )

    try:
        start_time = time.perf_counter()
        response = ORCHESTRATOR.llm.chat(
            messages=[
                {
                    "role": "user",
                    "content": 'Say \'ok\' in JSON format: {"status": "ok"}',
                }
            ],
            temperature=0.0,
            max_tokens=50,
            json_output=True,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if response.json_data and isinstance(response.json_data, dict):
            return LLMHealthResponse(
                status="ok",
                llm_mode=LLM_MODE,
                llm_provider="qwen",
                llm_model=ORCHESTRATOR.llm.model
                if hasattr(ORCHESTRATOR.llm, "model")
                else "qwen3.5-plus",
                llm_available=True,
                latency_ms=latency_ms,
                error=None,
            )
        else:
            return LLMHealthResponse(
                status="error",
                llm_mode=LLM_MODE,
                llm_provider="qwen",
                llm_model=ORCHESTRATOR.llm.model
                if hasattr(ORCHESTRATOR.llm, "model")
                else "qwen3.5-plus",
                llm_available=False,
                latency_ms=latency_ms,
                error="LLM returned invalid JSON",
            )
    except Exception as e:
        return LLMHealthResponse(
            status="error",
            llm_mode=LLM_MODE,
            llm_provider="qwen",
            llm_model=ORCHESTRATOR.llm.model
            if hasattr(ORCHESTRATOR.llm, "model")
            else "qwen3.5-plus",
            llm_available=False,
            latency_ms=None,
            error=str(e),
        )


@app.get("/health/verbose", response_model=HealthVerboseResponse)
def health_verbose() -> HealthVerboseResponse:
    import platform
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    index_dir = project_root / "index" / "chroma_bge_m3"
    data_dir = project_root / "data"
    models_dir = data_dir / "models"
    audio_dir = project_root / "dataset" / "raw" / "fma_small"

    components: dict[str, Any] = {
        "llm": {
            "status": "ok" if LLM_MODE == "qwen" else "mock",
            "mode": LLM_MODE,
            "provider": "qwen" if LLM_MODE == "qwen" else "mock",
        },
        "vector_index": {
            "status": "ok" if index_dir.exists() else "not_found",
            "path": str(index_dir),
            "exists": index_dir.exists(),
        },
        "audio_files": {
            "status": "ok" if audio_dir.exists() else "not_found",
            "path": str(audio_dir),
            "exists": audio_dir.exists(),
        },
        "behavior_data": {
            "path": str(data_dir / "processed" / "user_behaviors.jsonl"),
        },
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
        },
    }

    overall_status = "ok"
    for key in ["llm", "vector_index", "audio_files"]:
        if components[key].get("status") not in ["ok", "mock"]:
            overall_status = "degraded"
            break

    return HealthVerboseResponse(
        status=overall_status,
        llm_mode=LLM_MODE,
        components=components,
    )


@app.get("/behavior/stats")
def behavior_stats():
    return get_behavior_stats()


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest) -> FeedbackResponse:
    global LLM_DEBUG_INFO
    LLM_DEBUG_INFO = {
        "llm_enabled": LLM_MODE == "qwen",
        "llm_provider": "qwen" if LLM_MODE == "qwen" else "mock",
        "llm_model": ORCHESTRATOR.llm.model
        if hasattr(ORCHESTRATOR.llm, "model")
        else "mock",
        "llm_called": False,
        "fallback_used": False,
        "llm_latency_ms": 0,
    }

    state = SESSION_STORE.get(payload.session_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {payload.session_id}"
        )

    if LLM_MODE == "qwen":
        try:
            start_time = time.perf_counter()

            prompt_path = (
                Path(__file__).parent.parent
                / "llm"
                / "prompts"
                / "feedback_adaptation_prompt.txt"
            )
            prompt_template = prompt_path.read_text(encoding="utf-8")

            preference_state = state.get_state_summary()

            prompt = prompt_template.replace(
                "{preference_state_json}",
                json.dumps(preference_state, ensure_ascii=False),
            )
            prompt = prompt.replace("{feedback_type}", payload.feedback_type)
            prompt = prompt.replace(
                "{track_json}", json.dumps(payload.track_metadata, ensure_ascii=False)
            )
            prompt = prompt.replace(
                "{recommendation_context_json}",
                json.dumps(payload.recommendation_context, ensure_ascii=False),
            )

            response = ORCHESTRATOR.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
                json_output=True,
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            LLM_DEBUG_INFO["llm_called"] = True
            LLM_DEBUG_INFO["llm_latency_ms"] = latency_ms

            if response.json_data and isinstance(response.json_data, dict):
                result = response.json_data
                llm_check = result.get("llm_check", {})

                if llm_check.get("generated_by_llm"):
                    LLM_DEBUG_INFO["fallback_used"] = False

                    updated_state = result.get("updated_preference_state", {})
                    next_strategy = result.get("next_strategy", {})
                    ack_message = result.get("ack_message", "")

                    if payload.feedback_type == "like":
                        state.add_feedback(payload.track_id, "like")
                        logger.info(
                            f"[FEEDBACK] like track_id={payload.track_id} session_id={payload.session_id}"
                        )
                    elif payload.feedback_type == "dislike":
                        state.add_feedback(payload.track_id, "dislike")
                        state.exclude_ids = list(
                            set(state.exclude_ids + [payload.track_id])
                        )[:100]
                        logger.info(
                            f"[FEEDBACK] dislike track_id={payload.track_id} session_id={payload.session_id}"
                        )

                    return FeedbackResponse(
                        success=True,
                        ack_message=ack_message,
                        updated_preference_state=updated_state,
                        next_strategy=next_strategy,
                        recommendations=[],
                        debug=DebugInfo(**LLM_DEBUG_INFO),
                    )

        except Exception as e:
            logger.error(f"Feedback LLM error: {e}", exc_info=True)
            LLM_DEBUG_INFO["fallback_used"] = True

    ack_messages = {
        "like": "已记录你的喜欢，后续会为你推荐更多类似的歌曲。",
        "dislike": "已记录你的不喜欢，后续推荐将排除这首歌。",
        "refresh": "已排除上一批结果正在基于你当前偏好换一批推荐...",
    }

    content_recommendations: list[RecommendationObject] = []

    if payload.feedback_type == "like":
        if payload.track_id:
            state.add_feedback(payload.track_id, "like")
        track_title = (
            payload.track_metadata.get("title", "") if payload.track_metadata else ""
        )
        track_artist = (
            payload.track_metadata.get("artist", "") if payload.track_metadata else ""
        )
        track_genre = (
            payload.track_metadata.get("genre", "") if payload.track_metadata else ""
        )
        track_energy = (
            payload.track_metadata.get("energy_note", "none")
            if payload.track_metadata
            else "none"
        )
        song_name = f"{track_artist} - {track_title}" if track_artist else track_title
        _db_gen = get_db()
        _db = next(_db_gen)
        try:
            # 1. 记录行为到 user_behaviors 表
            record_behavior(
                user_id=str(state.user_id) if state.user_id else payload.session_id,
                song_id=payload.track_id or "",
                behavior_type="like",
                song_name=song_name,
                session_id=payload.session_id,
                metadata={
                    "title": track_title,
                    "artist": track_artist,
                },
                db=_db,
            )
            # 2. 更新用户偏好（新增）
            # state.user_id 是 str，需要转换为 int
            _user_id = state.user_id
            if _user_id and _user_id.isdigit():
                _user_id_int = int(_user_id)
                try:
                    UserPreference.record_like(
                        db=_db,
                        user_id=_user_id_int,
                        genre=track_genre,
                        energy=track_energy,
                    )
                    logger.info(
                        f"[PREFERENCE] liked genre={track_genre}, energy={track_energy} for user_id={_user_id_int}"
                    )
                except Exception as e:
                    logger.warning(f"[PREFERENCE] Failed to record like: {e}")
            # 3. 添加到"我喜欢的音乐"歌单（新增）
            if _user_id and _user_id.isdigit() and payload.track_id:
                try:
                    from src.api.playlist import get_or_create_liked_playlist
                    from src.models.playlist import PlaylistSong

                    _user_id_int = int(_user_id)
                    playlist = get_or_create_liked_playlist(_user_id_int, _db)
                    existing = (
                        _db.query(PlaylistSong)
                        .filter(
                            PlaylistSong.playlist_id == playlist.id,
                            PlaylistSong.track_id == payload.track_id,
                        )
                        .first()
                    )
                    if not existing:
                        song = PlaylistSong(
                            playlist_id=playlist.id, track_id=payload.track_id
                        )
                        _db.add(song)
                        _db.commit()
                        logger.info(
                            f"[PLAYLIST] Added track {payload.track_id} to liked playlist for user {_user_id_int}"
                        )
                except Exception as e:
                    logger.warning(f"[PLAYLIST] Failed to add to liked playlist: {e}")
        finally:
            try:
                next(_db_gen)
            except StopIteration:
                pass
        logger.info(
            f"[FEEDBACK] like track_id={payload.track_id} session_id={payload.session_id}"
        )

    elif payload.feedback_type == "dislike":
        if payload.track_id:
            state.add_feedback(payload.track_id, "dislike")
            state.exclude_ids = list(set(state.exclude_ids + [payload.track_id]))[:100]
            _db_gen2 = get_db()
            _db2 = next(_db_gen2)
            try:
                record_behavior(
                    user_id=str(state.user_id) if state.user_id else payload.session_id,
                    song_id=payload.track_id,
                    behavior_type="dislike",
                    session_id=payload.session_id,
                    db=_db2,
                )
                # 更新用户偏好（新增）
                _user_id_str = state.user_id
                _user_id_int = (
                    int(_user_id_str)
                    if _user_id_str and _user_id_str.isdigit()
                    else None
                )
                if _user_id_int:
                    track_genre = (
                        payload.track_metadata.get("genre", "")
                        if payload.track_metadata
                        else ""
                    )
                    if track_genre:
                        try:
                            UserPreference.record_dislike(
                                db=_db2,
                                user_id=_user_id_int,
                                genre=track_genre,
                            )
                            logger.info(
                                f"[PREFERENCE] disliked genre={track_genre} for user_id={_user_id_int}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"[PREFERENCE] Failed to record dislike: {e}"
                            )
            finally:
                try:
                    next(_db_gen2)
                except StopIteration:
                    pass
        logger.info(
            f"[FEEDBACK] dislike track_id={payload.track_id} session_id={payload.session_id} exclude_ids_count={len(state.exclude_ids)}"
        )
    elif payload.feedback_type == "refresh":
        if state.last_recommendation and state.last_recommendation.results:
            last_ids = [
                item.id
                for item in state.last_recommendation.results
                if hasattr(item, "id")
            ]
            state.exclude_ids = list(set(state.exclude_ids + last_ids))[:100]
            _db_gen3 = get_db()
            _db3 = next(_db_gen3)
            try:
                for tid in last_ids:
                    record_behavior(
                        user_id=str(state.user_id)
                        if state.user_id
                        else payload.session_id,
                        song_id=tid,
                        behavior_type="refresh_exclude",
                        session_id=payload.session_id,
                        db=_db3,
                    )
            finally:
                try:
                    next(_db_gen3)
                except StopIteration:
                    pass
        logger.info(
            f"[FEEDBACK] refresh session_id={payload.session_id} exclude_ids_count={len(state.exclude_ids)}"
        )

    return FeedbackResponse(
        success=True,
        ack_message=ack_messages.get(payload.feedback_type, "已收到反馈。"),
        updated_preference_state={},
        next_strategy={},
        recommendations=content_recommendations,
        debug=DebugInfo(**LLM_DEBUG_INFO),
    )


_DISPLAY_SCORE_MIN = 65
_DISPLAY_SCORE_MAX = 98
_DISPLAY_SCORE_TOP = 95
_DISPLAY_SCORE_BOTTOM = 75


def _calibrate_display_score(raw_score: float | None, rank: int, total: int) -> int:
    if total <= 0:
        return 85
    if total == 1:
        base = 90.0
    else:
        position_range = _DISPLAY_SCORE_TOP - _DISPLAY_SCORE_BOTTOM
        base = _DISPLAY_SCORE_TOP - (rank * position_range / (total - 1))
    adjustment = 0
    if raw_score is not None:
        if raw_score >= 0.5:
            adjustment = 3
        elif raw_score >= 0.35:
            adjustment = 0
        elif raw_score >= 0.26:
            adjustment = -2
        else:
            adjustment = -5
    display = base + adjustment
    return int(max(_DISPLAY_SCORE_MIN, min(_DISPLAY_SCORE_MAX, display)))


def _build_preference_suffix(state) -> str:
    clauses: list[str] = []
    energy = state.preference_profile.preferred_energy
    vocals = state.preference_profile.preferred_vocals
    energy_phrase_map = {
        "low": "安静 轻柔",
        "medium": "中等节奏 平衡",
        "high": "高能量 有节奏",
    }
    vocals_phrase_map = {
        "instrumental": "纯音乐 器乐",
        "vocal": "人声",
    }
    if energy and energy in energy_phrase_map:
        clauses.append(energy_phrase_map[energy])
    if vocals and vocals in vocals_phrase_map:
        clauses.append(vocals_phrase_map[vocals])
    genres = state.preference_profile.preferred_genres
    if genres:
        recent_genres = genres[-2:] if len(genres) > 2 else genres
        clauses.append(" ".join(recent_genres))
    return " ".join(clauses)


def _build_liked_context(state) -> str:
    if not state.liked_songs:
        return ""
    liked_ids = set(state.liked_songs[-10:])
    liked_genres: list[str] = []
    liked_artists: list[str] = []
    for record in state.recommendation_history:
        for item in record.results:
            if item.id in liked_ids:
                name = item.name or ""
                if " - " in name:
                    artist_part = name.split(" - ")[0].strip()
                    if artist_part and artist_part not in liked_artists:
                        liked_artists.append(artist_part)
                for citation in item.citations or []:
                    if "genre=" in str(citation):
                        genre_val = str(citation).split("genre=")[-1].strip()
                        if genre_val and genre_val not in liked_genres:
                            liked_genres.append(genre_val)
    clauses: list[str] = []
    if liked_genres:
        clauses.append(" ".join(liked_genres[-3:]))
    if liked_artists:
        clauses.append("类似 " + " ".join(liked_artists[-2:]) + " 的风格")
    return " ".join(clauses)


def _get_seed_song(state) -> str | None:
    if not state.liked_songs or not state.recommendation_history:
        return None
    liked_set = set(state.liked_songs[-10:])
    for record in reversed(state.recommendation_history):
        for item in record.results:
            if item.id in liked_set and item.name:
                name = str(item.name).strip()
                if name and " - " in name:
                    return name
    return None


@app.post("/recommend/refresh", response_model=RefreshResponse)
def recommend_refresh(payload: RefreshRequest) -> RefreshResponse:
    global LLM_DEBUG_INFO
    LLM_DEBUG_INFO = {
        "llm_enabled": LLM_MODE == "qwen",
        "llm_provider": "qwen" if LLM_MODE == "qwen" else "mock",
        "llm_model": ORCHESTRATOR.llm.model
        if hasattr(ORCHESTRATOR.llm, "model")
        else "mock",
        "llm_called": False,
        "fallback_used": False,
        "llm_latency_ms": 0,
    }

    state = SESSION_STORE.get(payload.session_id)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {payload.session_id}"
        )

    last_ids: list[str] = []
    if state.last_recommendation and state.last_recommendation.results:
        last_ids = [
            item.id for item in state.last_recommendation.results if hasattr(item, "id")
        ]
        state.exclude_ids = list(set(state.exclude_ids + last_ids))[:100]
        _db_gen_r = get_db()
        _db_r = next(_db_gen_r)
        try:
            for tid in last_ids:
                record_behavior(
                    user_id=str(state.user_id) if state.user_id else payload.session_id,
                    song_id=tid,
                    behavior_type="refresh_exclude",
                    session_id=payload.session_id,
                    db=_db_r,
                )
        finally:
            try:
                next(_db_gen_r)
            except StopIteration:
                pass

    parts = []
    if state.current_mood:
        parts.append(state.current_mood)
    if state.current_scene:
        parts.append(state.current_scene)
    if state.current_genre:
        parts.append(state.current_genre)
    synthetic_message = "继续推荐" if not parts else " ".join(parts) + "风格的音乐"

    turn_result = ORCHESTRATOR.handle_turn(synthetic_message, state)
    recommendations: list[RecommendationObject] = []
    if isinstance(turn_result, dict):
        recs = turn_result.get("recommendations")
        if isinstance(recs, list):
            for rec in recs:
                rec = dict(rec)
                evidence = rec.get("evidence")
                if isinstance(evidence, dict):
                    if rec.get("genre") is None:
                        rec["genre"] = evidence.get("genre")
                    if rec.get("genre_description") is None:
                        rec["genre_description"] = evidence.get("genre_description")
                    if not rec.get("tags"):
                        rec["tags"] = []
                    if isinstance(evidence.get("mood_tags"), list):
                        rec["tags"] = rec["tags"] + evidence["mood_tags"]
                    if isinstance(evidence.get("scene_tags"), list):
                        rec["tags"] = rec["tags"] + evidence["scene_tags"]
                    if isinstance(evidence.get("instrumentation"), list):
                        rec["tags"] = rec["tags"] + evidence["instrumentation"]
                    if evidence.get("energy_note"):
                        rec["tags"] = rec["tags"] + [evidence["energy_note"]]
                    rec["tags"] = list(dict.fromkeys(rec["tags"]))
                    if not rec.get("title"):
                        rec["title"] = evidence.get("title")
                    if not rec.get("artist"):
                        rec["artist"] = evidence.get("artist")

                rec_id = str(rec.get("id") or rec.get("track_id") or "")
                title = str(rec.get("title") or "")
                artist = str(rec.get("artist") or "")
                name = f"{artist} - {title}" if artist else title

                recommendations.append(
                    RecommendationObject(
                        id=rec_id,
                        name=name,
                        reason=str(rec.get("reason", "")),
                        citations=rec.get("citations") or [],
                        is_playable=rec.get("is_playable"),
                        audio_url=rec.get("audio_url"),
                        score=rec.get("score"),
                        display_score=rec.get("display_score"),
                        tags=rec.get("tags", []),
                        mood_tags=rec.get("mood_tags", []),
                        scene_tags=rec.get("scene_tags", []),
                        instrumentation=rec.get("instrumentation", []),
                        genre=str(rec.get("genre", "")),
                        style=rec.get("style"),
                        genre_description=rec.get("genre_description"),
                    )
                )

    SESSION_STORE.save_state(session_id=payload.session_id)

    logger.info(f"[REFRESH] session={payload.session_id} recs={len(recommendations)}")

    return RefreshResponse(
        session_id=payload.session_id,
        recommendations=recommendations,
        state=ChatStateResponse(
            mood=state.current_mood,
            scene=state.current_scene,
            genre=state.current_genre,
            preferred_energy=state.preference_profile.preferred_energy,
            preferred_vocals=state.preference_profile.preferred_vocals,
        ),
        debug=DebugInfo(**LLM_DEBUG_INFO),
    )
