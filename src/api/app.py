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

    def cf_recommend(args: dict[str, object]) -> dict[str, object]:
        song_name = str(args["song_name"])
        top_k = int(cast(int | float | str, args["top_k"]))
        exclude_ids = set(cast(list[str], args.get("exclude_ids") or []))

        seed = _mock_sha_seed(song_name)
        recommendations: list[dict[str, object]] = []
        for idx in range(40):
            rec_id = f"mock_cf_{seed}_{idx + 1:02d}"
            if rec_id in exclude_ids:
                continue

            recommendations.append(
                {
                    "id": rec_id,
                    "name": f"{song_name} - Similar #{idx + 1}",
                    "score": round(1.0 - 0.03 * idx, 4),
                }
            )
            if len(recommendations) >= top_k:
                break

        return {
            "ok": True,
            "data": {
                "matched_song": {"id": f"mock_seed_{seed}", "name": song_name},
                "recommendations": recommendations,
            },
        }

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
    cf_schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "song_name": {"type": "string"},
            "top_k": {"type": "integer"},
            "exclude_ids": {"type": "array"},
        },
        "required": ["song_name", "top_k"],
    }
    hybrid_schema: dict[str, object] = {
        "type": "object",
        "properties": {
            "query_text": {"type": "string"},
            "seed_song_name": {"type": "string"},
            "top_k": {"type": "integer"},
            "w_sem": {"type": "number"},
            "w_cf": {"type": "number"},
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
        name="cf_recommend",
        description="(mock) deterministic collaborative recommendation",
        parameters_schema=cf_schema,
        handler=cf_recommend,
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
                    }
                    for turn in new_turns
                ],
            )
        finally:
            db.close()

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
        "cf_model": {
            "status": "not_loaded",
            "path": str(models_dir / "implicit_model.pkl"),
            "ready": False,
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

    cf_recommendations: list[RecommendationObject] = []

    if payload.feedback_type == "like":
        if payload.track_id:
            state.add_feedback(payload.track_id, "like")
        track_title = (
            payload.track_metadata.get("title", "") if payload.track_metadata else ""
        )
        track_artist = (
            payload.track_metadata.get("artist", "") if payload.track_metadata else ""
        )
        song_name = f"{track_artist} - {track_title}" if track_artist else track_title
        _db_gen = get_db()
        _db = next(_db_gen)
        try:
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
        recommendations=cf_recommendations,
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


def _get_cf_seed_song(state) -> str | None:
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

    base_query = ""
    if state.last_recommendation and state.last_recommendation.query:
        base_query = state.last_recommendation.query
    else:
        parts = []
        if state.current_mood:
            parts.append(state.current_mood)
        if state.current_scene:
            parts.append(state.current_scene)
        if state.current_genre:
            parts.append(state.current_genre)
        base_query = " ".join(parts)

    preference_suffix = _build_preference_suffix(state)
    liked_suffix = _build_liked_context(state)
    effective_query = base_query
    if preference_suffix and preference_suffix not in effective_query:
        effective_query = f"{effective_query} {preference_suffix}".strip()
    if liked_suffix and liked_suffix not in effective_query:
        effective_query = f"{effective_query} {liked_suffix}".strip()

    top_k = 5
    seed_song = _get_cf_seed_song(state)

    tool_args: dict[str, object] = {
        "query_text": effective_query,
        "top_k": top_k,
        "exclude_ids": list(state.exclude_ids),
        "intent": "recommend_music",
    }
    if seed_song:
        tool_args["seed_song_name"] = seed_song

    tool_result = TOOL_REGISTRY.dispatch("hybrid_recommend", tool_args)
    raw_items: list[dict[str, object]] = []
    if tool_result.get("ok") is True:
        data = tool_result.get("data")
        if isinstance(data, list):
            raw_items = list(data)
        elif isinstance(data, dict):
            recs = data.get("recommendations")
            if isinstance(recs, list):
                raw_items = list(recs)

    recommendations: list[RecommendationObject] = []
    seen_ids: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        rec_id = str(item.get("track_id") or item.get("id") or "")
        if not rec_id or rec_id in seen_ids:
            continue
        seen_ids.add(rec_id)
        title = str(item.get("title") or "")
        artist = str(item.get("artist") or "")
        name = f"{artist} - {title}" if artist else title
        raw_score = item.get("score")
        score_float = float(raw_score) if isinstance(raw_score, (int, float)) else None
        display = _calibrate_display_score(score_float, len(recommendations), top_k)
        sources: list[str] = list(item.get("sources") or [])
        genre_desc_val = item.get("genre_description")
        genre_val = str(item.get("genre") or "")
        mood_tags_val = item.get("mood_tags")
        scene_tags_val = item.get("scene_tags")
        instrumentation_val = item.get("instrumentation")
        mood_tags: list[str] = (
            list(mood_tags_val) if isinstance(mood_tags_val, list) else []
        )
        scene_tags: list[str] = (
            list(scene_tags_val) if isinstance(scene_tags_val, list) else []
        )
        instrumentation: list[str] = (
            list(instrumentation_val) if isinstance(instrumentation_val, list) else []
        )
        tags: list[str] = (
            list(item.get("tags") or []) + mood_tags + scene_tags + instrumentation
        )
        tags = list(dict.fromkeys(tags))
        if genre_val and not genre_desc_val:
            from src.tools.semantic_search_tool import _derive_explanation_fields

            derived = _derive_explanation_fields(genre_val)
            genre_desc_val = derived.get("genre_description")
        rec_reason = item.get("reason")
        if not rec_reason:
            if "cf" in sources and "semantic" in sources:
                rec_reason = (
                    f"融合风格推荐：{genre_val}" if genre_val else "融合风格推荐"
                )
            elif "cf" in sources:
                rec_reason = (
                    f"相似用户推荐：{genre_val}" if genre_val else "相似用户推荐"
                )
            else:
                rec_reason = f"推荐歌曲：{genre_val}" if genre_val else "为你推荐"
        recommendations.append(
            RecommendationObject(
                id=rec_id,
                name=name,
                reason=rec_reason,
                citations=item.get("citations") or [],
                is_playable=item.get("is_playable"),
                audio_url=item.get("audio_url"),
                score=score_float,
                display_score=display,
                tags=tags,
                mood_tags=mood_tags,
                scene_tags=scene_tags,
                instrumentation=instrumentation,
                genre=genre_val,
                genre_description=genre_desc_val,
            )
        )

    state.add_recommendation(
        query=base_query,
        results=[{"id": r.id, "name": r.name} for r in recommendations],
        method="hybrid",
    )

    logger.info(
        f"[REFRESH] session={payload.session_id} query='{effective_query}' recs={len(recommendations)}"
    )

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
