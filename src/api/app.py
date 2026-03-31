from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import src.agent.orchestrator as orchestrator_module
from src.agent import MockLLMClient, Orchestrator
from src.api.session_store import SessionStore
from src.llm.clients import QwenClient
from src.llm.clients.base import ChatResponse
from src.llm.prompts.schemas import FEEDBACK_ADAPTATION_SCHEMA, RECOMMENDATION_EXPLANATION_SCHEMA
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
        seed_song_name = str(seed_song_name_obj) if seed_song_name_obj is not None else ""

        sem = semantic_search({"query_text": query_text, "top_k": top_k, "exclude_ids": exclude_ids})
        if sem.get("ok") is not True:
            return {"ok": False, "data": [], "error": "mock semantic_search failed"}

        sem_rows_obj = sem.get("data")
        sem_rows: list[object] = []
        if isinstance(sem_rows_obj, list):
            sem_rows = cast(list[object], sem_rows_obj)

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
                    "sources": ["semantic", "mock"],
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
    def _offline_retrieve_semantic_docs(query: str, top_k: int = 5) -> list[dict[str, object]]:
        _ = query
        _ = top_k
        return []

    setattr(orchestrator_module, "retrieve_semantic_docs", _offline_retrieve_semantic_docs)


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

FMA_SMALL_AUDIO_DIR = Path(__file__).parent.parent.parent / "dataset" / "raw" / "fma_small"
if FMA_SMALL_AUDIO_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/audio", StaticFiles(directory=str(FMA_SMALL_AUDIO_DIR)), name="audio")


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)


class ChatStateResponse(BaseModel):
    mood: str | None = None
    scene: str | None = None
    genre: str | None = None
    preferred_energy: str | None = None
    preferred_vocals: str | None = None


class RecommendationObject(BaseModel):
    id: str
    name: str
    reason: str | None = None
    citations: list[str] = Field(default_factory=list)
    is_playable: bool | None = None
    audio_url: str | None = None
    score: float | None = None
    display_score: int | None = None


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
    track_id: str
    track_metadata: dict[str, Any] = Field(default_factory=dict)
    recommendation_context: dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    success: bool
    ack_message: str = ""
    updated_preference_state: dict[str, Any] = Field(default_factory=dict)
    next_strategy: dict[str, Any] = Field(default_factory=dict)
    debug: DebugInfo = Field(default_factory=DebugInfo)


class LLMHealthResponse(BaseModel):
    status: str
    llm_mode: str
    llm_provider: str
    llm_model: str
    llm_available: bool
    latency_ms: int | None = None
    error: str | None = None


@app.post("/chat", response_model=ChatResponseModel)
def chat(payload: ChatRequest) -> ChatResponseModel:
    global LLM_DEBUG_INFO
    LLM_DEBUG_INFO = {
        "llm_enabled": LLM_MODE == "qwen",
        "llm_provider": "qwen" if LLM_MODE == "qwen" else "mock",
        "llm_model": ORCHESTRATOR.llm.model if hasattr(ORCHESTRATOR.llm, "model") else "mock",
        "llm_called": False,
        "fallback_used": False,
        "llm_latency_ms": 0,
    }

    session_id, state = SESSION_STORE.get_or_create(payload.session_id)
    
    start_time = time.perf_counter()
    turn_result = ORCHESTRATOR.handle_turn(payload.message, state)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    LLM_DEBUG_INFO["llm_called"] = state.llm_status in ("live", "live_verified")
    LLM_DEBUG_INFO["fallback_used"] = state.llm_status == "fallback"
    LLM_DEBUG_INFO["llm_latency_ms"] = latency_ms

    if isinstance(turn_result, dict):
        assistant_text = str(turn_result.get("assistant_text", ""))
        recommendations = turn_result.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []
    else:
        assistant_text = str(turn_result)
        recommendations = []

    return ChatResponseModel(
        session_id=session_id,
        assistant_text=assistant_text,
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


@app.post("/reset_session", response_model=ResetSessionResponse)
def reset_session(payload: ResetSessionRequest) -> ResetSessionResponse:
    return ResetSessionResponse(ok=SESSION_STORE.reset(payload.session_id))


@app.get("/session/{session_id}", response_model=SessionResponseModel)
def get_session(session_id: str) -> SessionResponseModel:
    state = SESSION_STORE.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return SessionResponseModel(ok=True, session_id=session_id, state=state.get_state_summary())


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
            messages=[{"role": "user", "content": "Say 'ok' in JSON format: {\"status\": \"ok\"}"}],
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
                llm_model=ORCHESTRATOR.llm.model if hasattr(ORCHESTRATOR.llm, "model") else "qwen3.5-plus",
                llm_available=True,
                latency_ms=latency_ms,
                error=None,
            )
        else:
            return LLMHealthResponse(
                status="error",
                llm_mode=LLM_MODE,
                llm_provider="qwen",
                llm_model=ORCHESTRATOR.llm.model if hasattr(ORCHESTRATOR.llm, "model") else "qwen3.5-plus",
                llm_available=False,
                latency_ms=latency_ms,
                error="LLM returned invalid JSON",
            )
    except Exception as e:
        return LLMHealthResponse(
            status="error",
            llm_mode=LLM_MODE,
            llm_provider="qwen",
            llm_model=ORCHESTRATOR.llm.model if hasattr(ORCHESTRATOR.llm, "model") else "qwen3.5-plus",
            llm_available=False,
            latency_ms=None,
            error=str(e),
        )


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest) -> FeedbackResponse:
    global LLM_DEBUG_INFO
    LLM_DEBUG_INFO = {
        "llm_enabled": LLM_MODE == "qwen",
        "llm_provider": "qwen" if LLM_MODE == "qwen" else "mock",
        "llm_model": ORCHESTRATOR.llm.model if hasattr(ORCHESTRATOR.llm, "model") else "mock",
        "llm_called": False,
        "fallback_used": False,
        "llm_latency_ms": 0,
    }

    state = SESSION_STORE.get(payload.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {payload.session_id}")

    if LLM_MODE == "qwen":
        try:
            start_time = time.perf_counter()
            
            prompt_path = Path(__file__).parent.parent / "llm" / "prompts" / "feedback_adaptation_prompt.txt"
            prompt_template = prompt_path.read_text(encoding="utf-8")

            preference_state = state.get_state_summary()
            
            prompt = prompt_template.replace("{preference_state_json}", json.dumps(preference_state, ensure_ascii=False))
            prompt = prompt.replace("{feedback_type}", payload.feedback_type)
            prompt = prompt.replace("{track_json}", json.dumps(payload.track_metadata, ensure_ascii=False))
            prompt = prompt.replace("{recommendation_context_json}", json.dumps(payload.recommendation_context, ensure_ascii=False))

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
                        logger.info(f"[FEEDBACK] like track_id={payload.track_id} session_id={payload.session_id}")
                    elif payload.feedback_type == "dislike":
                        state.add_feedback(payload.track_id, "dislike")
                        state.exclude_ids = list(set(state.exclude_ids + [payload.track_id]))[:100]
                        logger.info(f"[FEEDBACK] dislike track_id={payload.track_id} session_id={payload.session_id}")

                    return FeedbackResponse(
                        success=True,
                        ack_message=ack_message,
                        updated_preference_state=updated_state,
                        next_strategy=next_strategy,
                        debug=DebugInfo(**LLM_DEBUG_INFO),
                    )

        except Exception as e:
            logger.error(f"Feedback LLM error: {e}", exc_info=True)
            LLM_DEBUG_INFO["fallback_used"] = True

    ack_messages = {
        "like": "已记录你的喜欢，后续会为你推荐更多类似的歌曲。",
        "dislike": "已记录你的不喜欢，后续推荐将排除这首歌。",
        "refresh": "已排除上一批结果，正在基于你当前偏好换一批推荐...",
    }

    if payload.feedback_type == "like":
        state.add_feedback(payload.track_id, "like")
        logger.info(f"[FEEDBACK] like track_id={payload.track_id} session_id={payload.session_id}")
    elif payload.feedback_type == "dislike":
        state.add_feedback(payload.track_id, "dislike")
        state.exclude_ids = list(set(state.exclude_ids + [payload.track_id]))[:100]
        logger.info(f"[FEEDBACK] dislike track_id={payload.track_id} session_id={payload.session_id} exclude_ids_count={len(state.exclude_ids)}")
    elif payload.feedback_type == "refresh":
        # Fix: refresh should update exclude_ids with last recommendation IDs
        if state.last_recommendation and state.last_recommendation.results:
            last_ids = [item.id for item in state.last_recommendation.results if hasattr(item, 'id')]
            state.exclude_ids = list(set(state.exclude_ids + last_ids))[:100]
        logger.info(f"[FEEDBACK] refresh session_id={payload.session_id} exclude_ids_count={len(state.exclude_ids)}")

    return FeedbackResponse(
        success=True,
        ack_message=ack_messages.get(payload.feedback_type, "已收到反馈。"),
        updated_preference_state={},
        next_strategy={},
        debug=DebugInfo(**LLM_DEBUG_INFO),
    )
