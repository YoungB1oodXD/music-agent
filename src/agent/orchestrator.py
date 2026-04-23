from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

from src.config import (
    DISPLAY_SCORE_MIN,
    DISPLAY_SCORE_MAX,
    ORCHESTRATOR_ENABLE_LLM_INTENT,
    ORCHESTRATOR_ENABLE_PREFERENCE,
    ORCHESTRATOR_DEMO_MODE,
    ORCHESTRATOR_CANDIDATE_MULTIPLIER,
    ORCHESTRATOR_MAX_HISTORY_TURNS,
    ORCHESTRATOR_RAG_MAX_CHARS,
    ORCHESTRATOR_RAG_TOP_K,
    ORCHESTRATOR_TOOL_RESULTS_TOP_K,
    ORCHESTRATOR_TOOL_RESULTS_MAX_SOURCES,
)
from src.llm.clients.base import BaseLLMClient, ChatResponse
from src.llm.prompts.schemas import (
    FINAL_RESPONSE_SCHEMA,
    INTENT_AND_SLOTS_SCHEMA,
    PREFERENCE_PARSE_SCHEMA,
)
from src.manager.session_state import SessionState
from src.rag.context_builder import build_rag_context
from src.rag.retriever import retrieve_semantic_docs
from src.rag.sanitize import sanitize_untrusted_text
from src.tools.registry import ToolRegistry

_MAX_PROMPT_HISTORY_TURNS = ORCHESTRATOR_MAX_HISTORY_TURNS
_RAG_CONTEXT_MAX_CHARS = ORCHESTRATOR_RAG_MAX_CHARS
_RAG_RETRIEVAL_TOP_K = ORCHESTRATOR_RAG_TOP_K
_TOOL_RESULTS_PROMPT_TOP_K = ORCHESTRATOR_TOOL_RESULTS_TOP_K
_TOOL_RESULTS_PROMPT_MAX_SOURCES = ORCHESTRATOR_TOOL_RESULTS_MAX_SOURCES
_ENABLE_LLM_INTENT_EXTRACTION = ORCHESTRATOR_ENABLE_LLM_INTENT
_ENABLE_PREFERENCE_PARSING = ORCHESTRATOR_ENABLE_PREFERENCE
_DEMO_MODE_DEFAULT = ORCHESTRATOR_DEMO_MODE
_DEMO_MODE_CANDIDATE_MULTIPLIER = ORCHESTRATOR_CANDIDATE_MULTIPLIER

_DISPLAY_SCORE_MIN = DISPLAY_SCORE_MIN
_DISPLAY_SCORE_MAX = DISPLAY_SCORE_MAX
_DISPLAY_SCORE_TOP_POSITION = 95
_DISPLAY_SCORE_BOTTOM_POSITION = 75

_INTENT_RECOMMEND = "recommend_music"
_INTENT_SEARCH = "search_music"
_INTENT_REFINE = "refine_preferences"
_INTENT_EXPLAIN = "explain_why"
_INTENT_FEEDBACK = "feedback"

_ALLOWED_INTENTS = {
    _INTENT_RECOMMEND,
    _INTENT_SEARCH,
    _INTENT_REFINE,
    _INTENT_EXPLAIN,
    _INTENT_FEEDBACK,
}

_SLOT_INTENT = "intent"
_SLOT_QUERY_TEXT = "query_text"
_SLOT_MOOD = "mood"
_SLOT_SCENE = "scene"
_SLOT_GENRE = "genre"
_SLOT_ARTIST = "artist"
_SLOT_SONG_NAME = "song_name"
_SLOT_ENERGY = "energy"
_SLOT_VOCALS = "vocals"
_SLOT_TOP_K = "top_k"
_SLOT_FEEDBACK = "feedback"

_FEEDBACK_TYPE = "type"
_FEEDBACK_TARGET_ID = "target_id"

_FINAL_ASSISTANT_TEXT = "assistant_text"
_FINAL_RECOMMENDATIONS = "recommendations"
_FINAL_FOLLOWUP = "followup_question"

_INTENT_PROPERTIES = cast(
    dict[str, object], INTENT_AND_SLOTS_SCHEMA.get("properties", {})
)
_FINAL_PROPERTIES = cast(dict[str, object], FINAL_RESPONSE_SCHEMA.get("properties", {}))

if _SLOT_INTENT not in _INTENT_PROPERTIES or _SLOT_QUERY_TEXT not in _INTENT_PROPERTIES:
    raise ValueError("INTENT_AND_SLOTS_SCHEMA is missing required keys.")
if (
    _FINAL_ASSISTANT_TEXT not in _FINAL_PROPERTIES
    or _FINAL_RECOMMENDATIONS not in _FINAL_PROPERTIES
):
    raise ValueError("FINAL_RESPONSE_SCHEMA is missing required keys.")


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _as_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return None


def _as_list(value: object) -> list[object] | None:
    if isinstance(value, list):
        return cast(list[object], value)
    return None


def _clamp_top_k(value: object, default: int = 5) -> int:
    try:
        parsed = int(cast(int | float | str, value))
    except (TypeError, ValueError):
        return default
    return max(1, min(20, parsed))


def _calibrate_display_score(raw_score: float | None, rank: int, total: int) -> int:
    """
    Calibrate raw score to user-friendly display score (0-100).

    Strategy:
    1. Position-based base score: top=95, bottom=75
    2. Raw score adjustment: high raw -> bonus, low raw -> penalty
    3. Clamp to 65-98 range
    """
    if total <= 0:
        return 85

    if total == 1:
        base = 90
    else:
        position_range = _DISPLAY_SCORE_TOP_POSITION - _DISPLAY_SCORE_BOTTOM_POSITION
        base = _DISPLAY_SCORE_TOP_POSITION - (rank * position_range / (total - 1))

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


def _normalize_energy(value: object) -> str | None:
    normalized = _as_text(value).lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return None


def _normalize_vocals(value: object) -> str | None:
    normalized = _as_text(value).lower()
    if normalized in {"instrumental", "vocal"}:
        return normalized
    return None


class Orchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        tools: ToolRegistry,
        system_prompt_path: str | Path | None = None,
        max_tool_calls: int = 3,
    ) -> None:
        self.llm: BaseLLMClient = llm
        self.tools: ToolRegistry = tools
        self.max_tool_calls: int = max(0, min(3, max_tool_calls))

        prompt_path = (
            Path(system_prompt_path)
            if system_prompt_path is not None
            else Path(__file__).resolve().parent.parent
            / "llm"
            / "prompts"
            / "system_prompt.txt"
        )
        self.system_prompt: str = prompt_path.read_text(encoding="utf-8").strip()

    def handle_turn(self, user_text: str, state: SessionState) -> dict[str, object]:
        state.llm_status = "live"
        text = user_text.strip()
        if not text:
            reply = "请告诉我你想听什么类型的音乐，我可以马上帮你找。"
            state.add_dialogue_turn(
                user_input=user_text, system_response=reply, intent=None, entities={}
            )
            return {
                "assistant_text": reply,
                "recommendations": [],
                "recommendation_action": "replace",
            }

        base_intent_slots = self._extract_intent_and_slots(text, state)
        intent_slots = dict(base_intent_slots)
        query_text = _as_text(intent_slots.get(_SLOT_QUERY_TEXT)) or text

        base_intent = _as_text(intent_slots.get(_SLOT_INTENT)) or _INTENT_SEARCH
        if _ENABLE_PREFERENCE_PARSING and base_intent not in {
            _INTENT_FEEDBACK,
            _INTENT_EXPLAIN,
        }:
            preference_result = self._parse_preference_and_query(text, state)
            preference_slots = self._convert_preference_to_intent_slots(
                preference_result, state
            )
            intent_slots = self._merge_intent_slots(base_intent_slots, preference_slots)
            query_text = (
                _as_text(preference_result.get("retrieval_query")) or query_text
            )

        intent = self._resolve_dialogue_intent(text, intent_slots, state, base_intent)
        intent_slots[_SLOT_INTENT] = intent
        top_k = _clamp_top_k(intent_slots.get(_SLOT_TOP_K), default=5)

        mood = _as_text(intent_slots.get(_SLOT_MOOD))
        if mood:
            state.update_mood(mood)

        scene = _as_text(intent_slots.get(_SLOT_SCENE))
        if scene:
            state.update_scene(scene)

        genre = _as_text(intent_slots.get(_SLOT_GENRE))
        if genre:
            state.update_genre(genre)

        energy = _normalize_energy(intent_slots.get(_SLOT_ENERGY))
        if energy is None:
            energy = self._extract_energy(text)
            if energy is not None:
                intent_slots[_SLOT_ENERGY] = energy

        vocals = _normalize_vocals(intent_slots.get(_SLOT_VOCALS))
        if vocals is None:
            vocals = self._extract_vocals(text)
            if vocals is not None:
                intent_slots[_SLOT_VOCALS] = vocals

        if energy is not None or vocals is not None:
            state.update_preference(energy=energy, vocals=vocals)

        excluded_artist = self._extract_excluded_artist(text)
        if excluded_artist:
            state.add_excluded_artist(excluded_artist)

        if self._is_refresh_request(text):
            refresh_ids = self._collect_recommended_ids(state, cap=100)
            state.exclude_ids = self._merge_ids(state.exclude_ids, refresh_ids, cap=100)
            if state.last_recommendation and state.last_recommendation.query:
                query_text = state.last_recommendation.query

        if intent == _INTENT_FEEDBACK:
            self._apply_feedback(intent_slots, state)

        tool_plan = self._build_tool_plan(
            intent, intent_slots, query_text, top_k, state
        )
        tool_results = self._dispatch_tools(tool_plan)

        rag_context = self._build_rag_context(query_text)
        recommendations, method = self._extract_recommendations(
            tool_results, top_k=top_k
        )

        final_payload = self._compose_final_payload(
            user_text=text,
            state=state,
            intent_slots=intent_slots,
            query_text=query_text,
            rag_context=rag_context,
            tool_results=tool_results,
            recommendations=recommendations,
        )

        reply = _as_text(final_payload.get(_FINAL_ASSISTANT_TEXT))
        final_recommendations = (
            _as_list(final_payload.get(_FINAL_RECOMMENDATIONS)) or []
        )
        recommendation_action = "replace"
        if intent in {_INTENT_EXPLAIN, _INTENT_FEEDBACK}:
            recommendation_action = "preserve"

        if final_recommendations and method is not None:
            state.add_recommendation(
                query=query_text,
                results=final_recommendations,
                method=method,
            )

        entities = self._build_entities(intent_slots)
        state.add_dialogue_turn(
            user_input=user_text,
            system_response=reply,
            intent=intent,
            entities=entities,
        )
        return {
            "assistant_text": reply,
            "recommendations": final_recommendations,
            "recommendation_action": recommendation_action,
        }

    def _extract_intent_and_slots(
        self, user_text: str, state: SessionState
    ) -> dict[str, object]:
        if not _ENABLE_LLM_INTENT_EXTRACTION:
            return self._deterministic_intent_slots(user_text, state)

        payload: dict[str, object] = {
            "user_text": user_text,
            "context": state.get_context_summary(),
            "state_summary": state.get_state_summary(),
            "recent_dialogues": state.get_recent_dialogue(max_turns=5),
            "schema": INTENT_AND_SLOTS_SCHEMA,
        }
        prompt = (
            "请基于 INTENT_AND_SLOTS_SCHEMA 输出严格 JSON。"
            "只返回 JSON 对象，不要返回任何额外文本。\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            response = self.llm.chat(
                messages=self._build_messages(state, prompt),
                temperature=0.0,
                max_tokens=400,
                json_output=True,
            )
            parsed = self._parse_chat_json(response)
            if parsed is not None:
                normalized = self._normalize_intent_slots(parsed)
                if normalized.get(_SLOT_QUERY_TEXT):
                    return normalized
        except Exception:
            state.llm_status = "fallback"

        return self._deterministic_intent_slots(user_text, state)

    def _parse_preference_and_query(
        self, user_text: str, state: SessionState
    ) -> dict[str, object]:
        preference_prompt_path = (
            Path(__file__).resolve().parent.parent
            / "llm"
            / "prompts"
            / "preference_parse_prompt.txt"
        )
        preference_prompt = preference_prompt_path.read_text(encoding="utf-8").strip()

        previous_state = state.get_state_summary()
        conversation_history = state.get_recent_dialogue(max_turns=5)

        prompt = preference_prompt.replace(
            "{previous_state_json}", json.dumps(previous_state, ensure_ascii=False)
        )
        prompt = prompt.replace(
            "{conversation_history}",
            json.dumps(conversation_history, ensure_ascii=False),
        )
        prompt = prompt.replace("{latest_user_message}", user_text)

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
                json_output=True,
            )
            parsed = self._parse_chat_json(response)
            if parsed is not None:
                llm_check = _as_dict(parsed.get("llm_check"))
                if llm_check and llm_check.get("generated_by_llm") is True:
                    return parsed
        except Exception:
            state.llm_status = "fallback"

        return self._deterministic_intent_slots(user_text, state)

    def _convert_preference_to_intent_slots(
        self, preference_result: dict[str, object], state: SessionState
    ) -> dict[str, object]:
        result: dict[str, object] = {_SLOT_INTENT: _INTENT_RECOMMEND}

        updated_state = (
            _as_dict(preference_result.get("updated_preference_state")) or {}
        )

        scene = _as_text(updated_state.get("scene"))
        if scene:
            result[_SLOT_SCENE] = scene

        mood_list = _as_list(updated_state.get("mood"))
        if mood_list:
            result[_SLOT_MOOD] = ", ".join(
                _as_text(m) for m in mood_list if _as_text(m)
            )

        energy = _as_text(updated_state.get("energy"))
        if energy:
            result[_SLOT_ENERGY] = energy

        vocal_pref = _as_text(updated_state.get("vocal_preference"))
        if vocal_pref:
            result[_SLOT_VOCALS] = (
                "instrumental" if "instrumental" in vocal_pref.lower() else "vocal"
            )

        genre_list = _as_list(updated_state.get("genre_preferences"))
        if genre_list:
            result[_SLOT_GENRE] = ", ".join(
                _as_text(g) for g in genre_list if _as_text(g)
            )

        llm_check = _as_dict(preference_result.get("llm_check"))
        if llm_check and llm_check.get("generated_by_llm"):
            state.llm_status = "live_verified"
            logger.info(
                f"[LLM VERIFIED] signature: {_as_text(llm_check.get('llm_signature'))}"
            )

        return result

    @staticmethod
    def _merge_intent_slots(
        base_slots: dict[str, object], preference_slots: dict[str, object]
    ) -> dict[str, object]:
        merged = dict(base_slots)
        for key, value in preference_slots.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            merged[key] = value
        return merged

    def _resolve_dialogue_intent(
        self,
        user_text: str,
        intent_slots: dict[str, object],
        state: SessionState,
        base_intent: str,
    ) -> str:
        if base_intent in {_INTENT_EXPLAIN, _INTENT_FEEDBACK}:
            return base_intent
        if self._is_refresh_request(user_text):
            return _INTENT_REFINE

        has_preference_update = any(
            [
                _as_text(intent_slots.get(_SLOT_MOOD)),
                _as_text(intent_slots.get(_SLOT_SCENE)),
                _as_text(intent_slots.get(_SLOT_GENRE)),
                _normalize_energy(intent_slots.get(_SLOT_ENERGY)),
                _normalize_vocals(intent_slots.get(_SLOT_VOCALS)),
                self._extract_excluded_artist(user_text),
            ]
        )

        if has_preference_update and state.last_recommendation is not None:
            return _INTENT_REFINE
        return base_intent

    def _build_messages(
        self, state: SessionState, current_user_prompt: str
    ) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        history_turns = state.dialogue_history[-_MAX_PROMPT_HISTORY_TURNS:]
        for turn in history_turns:
            messages.append({"role": "user", "content": turn.user_input})
            messages.append({"role": "assistant", "content": turn.system_response})
        messages.append({"role": "user", "content": current_user_prompt})
        return messages

    @staticmethod
    def _parse_chat_json(response: ChatResponse) -> dict[str, object] | None:
        json_data = _as_dict(response.json_data)
        if json_data is not None:
            return json_data

        content = _as_text(response.content)
        if not content:
            return None

        try:
            parsed_dict = TypeAdapter(dict[str, object]).validate_json(content)
        except ValidationError:
            return None
        return parsed_dict

    def _normalize_intent_slots(self, payload: dict[str, object]) -> dict[str, object]:
        result: dict[str, object] = {}

        intent = _as_text(payload.get(_SLOT_INTENT))
        if intent not in _ALLOWED_INTENTS:
            intent = _INTENT_SEARCH
        result[_SLOT_INTENT] = intent

        query_text = _as_text(payload.get(_SLOT_QUERY_TEXT))
        if query_text:
            result[_SLOT_QUERY_TEXT] = query_text

        for key in (
            _SLOT_MOOD,
            _SLOT_SCENE,
            _SLOT_GENRE,
            _SLOT_ARTIST,
            _SLOT_SONG_NAME,
        ):
            value = _as_text(payload.get(key))
            if value:
                result[key] = value

        energy = _normalize_energy(payload.get(_SLOT_ENERGY))
        if energy is not None:
            result[_SLOT_ENERGY] = energy

        vocals = _normalize_vocals(payload.get(_SLOT_VOCALS))
        if vocals is not None:
            result[_SLOT_VOCALS] = vocals

        result[_SLOT_TOP_K] = _clamp_top_k(payload.get(_SLOT_TOP_K), default=5)

        feedback_obj = _as_dict(payload.get(_SLOT_FEEDBACK))
        if feedback_obj is not None:
            feedback_type = _as_text(feedback_obj.get(_FEEDBACK_TYPE))
            if feedback_type in {"like", "dislike", "skip"}:
                normalized_feedback: dict[str, object] = {_FEEDBACK_TYPE: feedback_type}
                target_id = _as_text(feedback_obj.get(_FEEDBACK_TARGET_ID))
                if target_id:
                    normalized_feedback[_FEEDBACK_TARGET_ID] = target_id
                result[_SLOT_FEEDBACK] = normalized_feedback

        return result

    def _deterministic_intent_slots(
        self, user_text: str, state: SessionState
    ) -> dict[str, object]:
        lowered = user_text.lower()

        intent = _INTENT_SEARCH
        if any(token in lowered for token in ("为什么", "理由", "explain")):
            intent = _INTENT_EXPLAIN
        elif any(
            token in lowered
            for token in ("不喜欢", "跳过", "dislike", "skip", "like", "喜欢")
        ):
            intent = _INTENT_FEEDBACK
        elif any(token in user_text for token in ("换一批", "再来一批", "换批")):
            intent = _INTENT_REFINE
        elif any(token in lowered for token in ("换", "再来", "调整", "refine")):
            intent = _INTENT_REFINE
        elif any(token in lowered for token in ("推荐", "来点", "听点", "recommend")):
            intent = _INTENT_RECOMMEND

        result: dict[str, object] = {
            _SLOT_INTENT: intent,
            _SLOT_QUERY_TEXT: user_text,
            _SLOT_TOP_K: self._extract_top_k(user_text),
        }

        mood = self._extract_mood(user_text)
        if mood:
            result[_SLOT_MOOD] = mood

        scene = self._extract_scene(user_text)
        if scene:
            result[_SLOT_SCENE] = scene

        energy = self._extract_energy(user_text)
        if energy:
            result[_SLOT_ENERGY] = energy

        vocals = self._extract_vocals(user_text)
        if vocals:
            result[_SLOT_VOCALS] = vocals

        song_name = self._extract_song_name(user_text)
        if song_name:
            result[_SLOT_SONG_NAME] = song_name

        if intent == _INTENT_FEEDBACK:
            feedback = self._extract_feedback(user_text, state)
            if feedback:
                result[_SLOT_FEEDBACK] = feedback

        return result

    @staticmethod
    def _extract_top_k(user_text: str) -> int:
        match = re.search(r"(\d{1,2})\s*首", user_text)
        if not match:
            return 5
        return _clamp_top_k(match.group(1), default=5)

    @staticmethod
    def _extract_mood(user_text: str) -> str | None:
        mood_map: list[tuple[str, str]] = [
            ("放松", "放松"),
            ("平静", "平静"),
            ("开心", "开心"),
            ("伤心", "伤感"),
            ("治愈", "治愈"),
            ("兴奋", "兴奋"),
        ]
        for keyword, normalized in mood_map:
            if keyword in user_text:
                return normalized
        return None

    @staticmethod
    def _extract_scene(user_text: str) -> str | None:
        scene_map: list[tuple[str, str]] = [
            ("学习", "学习"),
            ("工作", "工作"),
            ("跑步", "跑步"),
            ("运动", "运动"),
            ("健身", "运动"),
            ("睡前", "睡前"),
            ("通勤", "通勤"),
            ("开车", "通勤"),
            ("聚会", "聚会"),
            ("旅行", "旅行"),
        ]
        for keyword, normalized in scene_map:
            if keyword in user_text:
                return normalized
        return None

    @staticmethod
    def _extract_energy(user_text: str) -> str | None:
        lowered = user_text.lower()
        if "不要太吵" in user_text or "安静" in user_text or "轻柔" in user_text:
            return "low"
        if (
            "high energy" in lowered
            or "高能量" in user_text
            or "欢快" in user_text
            or "更燃" in user_text
            or "有活力" in user_text
            or "跑步" in user_text
            or "运动" in user_text
        ):
            return "high"
        if "中等能量" in user_text:
            return "medium"
        return None

    @staticmethod
    def _extract_vocals(user_text: str) -> str | None:
        lowered = user_text.lower()
        if (
            "来点纯音乐" in user_text
            or "纯音乐" in user_text
            or "instrumental" in lowered
        ):
            return "instrumental"
        if "人声" in user_text or "vocal" in lowered:
            return "vocal"
        return None

    @staticmethod
    def _extract_excluded_artist(user_text: str) -> str | None:
        patterns = [
            r"不要[再]?[推荐听]?[给]?我?([^\s]+?)(?:的歌|的作品|的歌了)",
            r"别[再]?[推荐听]?[给]?我?([^\s]+?)(?:的歌|的作品)",
            r"不要是([^\s]+?)(?:了|了)",
            r"别再[推荐听]?([^\s]+?)(?:的歌|的作品)",
            r"排除([^\s]+?)(?:的歌|的作品|)",
            r"不要([^\s]+?)(?:的歌|的作品)",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_text)
            if match:
                artist = match.group(1).strip()
                if artist and len(artist) < 50 and len(artist) > 1:
                    return artist
        return None

    @staticmethod
    def _extract_song_name(user_text: str) -> str | None:
        title_match = re.search(r"《([^》]+)》", user_text)
        if title_match:
            name = title_match.group(1).strip()
            if name:
                return name

        quote_match = re.search(r"\"([^\"]+)\"", user_text)
        if quote_match:
            name = quote_match.group(1).strip()
            if name:
                return name
        return None

    @staticmethod
    def _extract_feedback(
        user_text: str, state: SessionState
    ) -> dict[str, object] | None:
        lowered = user_text.lower()
        feedback_type = ""
        if "不喜欢" in user_text or "dislike" in lowered:
            feedback_type = "dislike"
        elif "跳过" in user_text or "skip" in lowered:
            feedback_type = "skip"
        elif "喜欢" in user_text or "like" in lowered:
            feedback_type = "like"

        if not feedback_type:
            return None

        target_match = re.search(
            r"(?:id[:：\s]*)([A-Za-z0-9_\-]+)", user_text, re.IGNORECASE
        )
        target_id = target_match.group(1).strip() if target_match else ""
        if (
            not target_id
            and state.last_recommendation is not None
            and state.last_recommendation.results
        ):
            target_id = state.last_recommendation.results[0].id

        feedback: dict[str, object] = {_FEEDBACK_TYPE: feedback_type}
        if target_id:
            feedback[_FEEDBACK_TARGET_ID] = target_id
        return feedback

    def _apply_feedback(
        self, intent_slots: dict[str, object], state: SessionState
    ) -> None:
        feedback_obj = _as_dict(intent_slots.get(_SLOT_FEEDBACK))
        if feedback_obj is None:
            feedback_obj = self._extract_feedback(
                _as_text(intent_slots.get(_SLOT_QUERY_TEXT)), state
            )
            if feedback_obj is None:
                return

        feedback_type = _as_text(feedback_obj.get(_FEEDBACK_TYPE))
        if feedback_type not in {"like", "dislike", "skip"}:
            return

        target_id = _as_text(feedback_obj.get(_FEEDBACK_TARGET_ID))
        if (
            not target_id
            and state.last_recommendation is not None
            and state.last_recommendation.results
        ):
            target_id = state.last_recommendation.results[0].id
        if not target_id:
            return

        state.add_feedback(target_id, feedback_type)
        if feedback_type in {"dislike", "skip"}:
            state.exclude_ids = self._merge_ids(state.exclude_ids, [target_id], cap=100)

    @staticmethod
    def _is_refresh_request(user_text: str) -> bool:
        refresh_tokens = ("换一批", "再来一批", "换批")
        return any(token in user_text for token in refresh_tokens)

    @staticmethod
    def _merge_ids(
        existing: list[str], incoming: list[str], cap: int = 100
    ) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()

        for raw in [*existing, *incoming]:
            normalized = raw.strip()
            if not normalized or normalized in seen:
                continue
            merged.append(normalized)
            seen.add(normalized)

        if len(merged) > cap:
            return merged[-cap:]
        return merged

    @staticmethod
    def _collect_recommended_ids(state: SessionState, cap: int = 100) -> list[str]:
        collected: list[str] = []

        if state.last_recommendation is not None:
            collected.extend(item.id for item in state.last_recommendation.results)

        for record in state.recommendation_history:
            collected.extend(item.id for item in record.results)

        return Orchestrator._merge_ids([], collected, cap=cap)

    @staticmethod
    def _build_preference_suffix(
        state: SessionState, intent_slots: dict[str, object]
    ) -> str:
        energy = _normalize_energy(intent_slots.get(_SLOT_ENERGY))
        if energy is None:
            energy = _normalize_energy(state.preference_profile.preferred_energy)

        vocals = _normalize_vocals(intent_slots.get(_SLOT_VOCALS))
        if vocals is None:
            vocals = _normalize_vocals(state.preference_profile.preferred_vocals)

        energy_phrase_map = {
            "low": "安静 轻柔",
            "medium": "中等节奏 平衡",
            "high": "高能量 有节奏",
        }
        vocals_phrase_map = {
            "instrumental": "纯音乐 器乐",
            "vocal": "人声",
        }

        clauses: list[str] = []
        if energy is not None:
            phrase = energy_phrase_map.get(energy)
            if phrase:
                clauses.append(phrase)
        if vocals is not None:
            phrase = vocals_phrase_map.get(vocals)
            if phrase:
                clauses.append(phrase)

        # Add accumulated genres (last 2)
        genres = state.preference_profile.preferred_genres
        if genres:
            recent_genres = genres[-2:] if len(genres) > 2 else genres
            clauses.append(" ".join(recent_genres))

        return " ".join(clauses)

    @staticmethod
    def _build_liked_context(state: SessionState) -> str:
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

    def _build_tool_plan(
        self,
        intent: str,
        intent_slots: dict[str, object],
        query_text: str,
        top_k: int,
        state: SessionState,
    ) -> list[tuple[str, dict[str, object]]]:
        if self.max_tool_calls <= 0:
            return []

        song_name = _as_text(intent_slots.get(_SLOT_SONG_NAME))
        if intent in {_INTENT_FEEDBACK, _INTENT_EXPLAIN}:
            return []

        exclude_ids = list(state.exclude_ids)
        exclude_artists = list(state.exclude_artists) if state.exclude_artists else []
        preference_suffix = self._build_preference_suffix(state, intent_slots)
        liked_suffix = self._build_liked_context(state)
        effective_query_text = query_text
        suffix_parts = []
        if preference_suffix and preference_suffix not in effective_query_text:
            suffix_parts.append(preference_suffix)
        if liked_suffix and liked_suffix not in effective_query_text:
            suffix_parts.append(liked_suffix)
        if suffix_parts:
            effective_query_text = (
                f"{effective_query_text} {' '.join(suffix_parts)}".strip()
            )

        candidate_k = top_k * _DEMO_MODE_CANDIDATE_MULTIPLIER

        tool_args: dict[str, object] = {
            "query_text": effective_query_text,
            "top_k": candidate_k,
            "exclude_ids": exclude_ids,
            "intent": intent,
        }
        if exclude_artists:
            tool_args["exclude_artists"] = exclude_artists

        return [("hybrid_recommend", tool_args)]

    def _dispatch_tools(
        self, tool_plan: list[tuple[str, dict[str, object]]]
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for tool_name, args in tool_plan[: self.max_tool_calls]:
            dispatch_result = self.tools.dispatch(tool_name, args)
            records.append({"name": tool_name, "args": args, "result": dispatch_result})
        return records

    def _build_rag_context(self, query_text: str) -> str:
        try:
            docs = retrieve_semantic_docs(query_text, _RAG_RETRIEVAL_TOP_K)
        except Exception:
            docs = []

        safe_docs: list[dict[str, object]] = []
        for doc in docs:
            safe_doc: dict[str, object] = {}
            for key, value in doc.items():
                if isinstance(value, str):
                    safe_doc[key] = sanitize_untrusted_text(value)
                else:
                    safe_doc[key] = value
            safe_docs.append(safe_doc)

        return build_rag_context(safe_docs, max_chars=_RAG_CONTEXT_MAX_CHARS)

    @staticmethod
    def _summarize_sources(value: object) -> list[str]:
        sources_raw = _as_list(value)
        if sources_raw is None:
            return []
        sources: list[str] = []
        for source_obj in sources_raw[:_TOOL_RESULTS_PROMPT_MAX_SOURCES]:
            source = _as_text(source_obj)
            if source:
                sources.append(source)
        return sources

    @staticmethod
    def _summarize_result_row(row_obj: object) -> dict[str, object] | None:
        row = _as_dict(row_obj)
        if row is None:
            return None

        summary: dict[str, object] = {}
        rec_id = _as_text(row.get("id")) or _as_text(row.get("track_id"))
        if rec_id:
            summary["id"] = rec_id

        for key in ("title", "artist", "genre"):
            val = _as_text(row.get(key))
            if val:
                summary[key] = val

        for score_key in ("similarity", "cf_score"):
            score_value = row.get(score_key)
            if isinstance(score_value, (int, float)):
                summary[score_key] = float(score_value)

        sources = Orchestrator._summarize_sources(row.get("sources"))
        if sources:
            summary["sources"] = sources

        return summary if summary else None

    @staticmethod
    def _summarize_tool_result_data(data: object) -> list[dict[str, object]]:
        if isinstance(data, dict):
            recommendations = (
                _as_list(cast(dict[str, object], data).get("recommendations")) or []
            )
            rows = recommendations[:_TOOL_RESULTS_PROMPT_TOP_K]
            summarized: list[dict[str, object]] = []
            for row_obj in rows:
                row_summary = Orchestrator._summarize_result_row(row_obj)
                if row_summary is not None:
                    summarized.append(row_summary)
            return summarized

        rows = _as_list(data)
        if rows is None:
            return []

        summarized_rows: list[dict[str, object]] = []
        for row_obj in rows[:_TOOL_RESULTS_PROMPT_TOP_K]:
            row_summary = Orchestrator._summarize_result_row(row_obj)
            if row_summary is not None:
                summarized_rows.append(row_summary)
        return summarized_rows

    def _summarize_tool_results_for_prompt(
        self, tool_results: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        summarized_results: list[dict[str, object]] = []
        for row in tool_results:
            tool_name = _as_text(row.get("name"))
            result = _as_dict(row.get("result"))
            if not tool_name or result is None:
                continue

            summary_row: dict[str, object] = {
                "name": tool_name,
                "ok": result.get("ok") is True,
            }
            error_text = _as_text(result.get("error"))
            if error_text:
                summary_row["error"] = error_text

            summary_data = self._summarize_tool_result_data(result.get("data"))
            if summary_data:
                summary_row["data"] = summary_data

            summarized_results.append(summary_row)
        return summarized_results

    def _extract_recommendations(
        self,
        tool_results: list[dict[str, object]],
        top_k: int = 5,
    ) -> tuple[list[dict[str, object]], str | None]:
        method_map = {
            "semantic_search": "semantic",
            "hybrid_recommend": "content",
        }

        for row in tool_results:
            tool_name = _as_text(row.get("name"))
            result = _as_dict(row.get("result"))
            if not tool_name or result is None:
                continue
            if result.get("ok") is not True:
                continue

            recommendations = self._extract_recommendations_for_tool(
                tool_name, result.get("data")
            )
            if not recommendations:
                continue

            method = method_map.get(tool_name)
            if method is None:
                continue

            if _DEMO_MODE_DEFAULT:
                playable = [r for r in recommendations if r.get("is_playable") is True]
                non_playable = [
                    r for r in recommendations if r.get("is_playable") is not True
                ]

                if len(playable) >= top_k:
                    recommendations = playable[:top_k]
                else:
                    recommendations = (
                        playable + non_playable[: max(0, top_k - len(playable))]
                    )
            else:
                recommendations = recommendations[:top_k]

            return recommendations, method

        return [], None

    def _extract_recommendations_for_tool(
        self, tool_name: str, data: object
    ) -> list[dict[str, object]]:
        rows = _as_list(data)
        if rows is None:
            return []
        return self._build_recommendations_from_rows(
            rows, use_cf_fields=False, tool_name=tool_name
        )

    @staticmethod
    def _build_recommendations_from_rows(
        rows: list[object],
        use_cf_fields: bool,
        tool_name: str = "",
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        seen_ids: set[str] = set()

        for row_obj in rows:
            row = _as_dict(row_obj)
            if row is None:
                continue

            if use_cf_fields:
                rec_id = _as_text(row.get("id"))
                name = _as_text(row.get("name"))
            else:
                rec_id = _as_text(row.get("track_id")) or _as_text(row.get("id"))
                title = _as_text(row.get("title"))
                artist = _as_text(row.get("artist"))
                if artist and title:
                    name = f"{artist} - {title}"
                elif title:
                    name = title
                else:
                    name = _as_text(row.get("name"))

            if not rec_id or rec_id in seen_ids:
                continue
            if not name:
                name = rec_id

            seen_ids.add(rec_id)

            # Keep original row data but ensure id and name are present
            item = dict(row)
            item["id"] = rec_id
            item["name"] = name
            item["_tool"] = tool_name
            results.append(item)

        return results

    def _compose_final_payload(
        self,
        user_text: str,
        state: SessionState,
        intent_slots: dict[str, object],
        query_text: str,
        rag_context: str,
        tool_results: list[dict[str, object]],
        recommendations: list[dict[str, object]],
    ) -> dict[str, object]:
        tool_failures = self._collect_tool_failures(tool_results)
        if tool_results and len(tool_failures) == len(tool_results):
            error_text = tool_failures[0] if tool_failures else "工具调用失败"
            reply = f"抱歉，这次工具调用没有成功（{error_text}）。你可以换个关键词，我继续帮你找。"
            return {
                _FINAL_ASSISTANT_TEXT: reply,
                _FINAL_RECOMMENDATIONS: [],
            }

        seed_recommendations = self._build_seed_recommendations(recommendations)
        final_payload = self._generate_final_response(
            state=state,
            intent_slots=intent_slots,
            query_text=query_text,
            rag_context=rag_context,
            tool_results=tool_results,
            seed_recommendations=seed_recommendations,
            tool_failures=tool_failures,
        )

        assistant_text = _as_text(final_payload.get(_FINAL_ASSISTANT_TEXT))
        followup = _as_text(final_payload.get(_FINAL_FOLLOWUP))
        if not assistant_text:
            assistant_text = self._fallback_reply(
                user_text, intent_slots, recommendations, tool_failures
            )
        elif followup:
            assistant_text = f"{assistant_text}\n{followup}"

        final_payload[_FINAL_ASSISTANT_TEXT] = assistant_text
        return final_payload

    def _collect_tool_failures(
        self, tool_results: list[dict[str, object]]
    ) -> list[str]:
        failures: list[str] = []
        for row in tool_results:
            result = _as_dict(row.get("result"))
            if result is None:
                continue
            if result.get("ok") is True:
                continue
            error_text = _as_text(result.get("error"))
            failures.append(error_text or "工具调用失败")
        return failures

    @staticmethod
    def _build_seed_recommendations(
        recommendations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        seed_rows: list[dict[str, object]] = []
        for row in recommendations:
            rec_id = _as_text(row.get("id"))
            name = _as_text(row.get("name"))
            if not rec_id or not name:
                continue

            tool_name = _as_text(row.get("_tool"))
            citations = ["tool_results"]

            evidence: dict[str, object] = {}
            artist = _as_text(row.get("artist"))
            genre = _as_text(row.get("genre"))
            title = _as_text(row.get("title"))
            if artist:
                evidence["artist"] = artist
            if genre:
                evidence["genre"] = genre
            if title:
                evidence["title"] = title

            genre_description = row.get("genre_description")
            mood_tags = row.get("mood_tags")
            scene_tags = row.get("scene_tags")
            instrumentation = row.get("instrumentation")
            energy_note = row.get("energy_note")
            if genre_description:
                evidence["genre_description"] = genre_description
            if mood_tags:
                evidence["mood_tags"] = mood_tags
            if scene_tags:
                evidence["scene_tags"] = scene_tags
            if instrumentation:
                evidence["instrumentation"] = instrumentation
            if energy_note:
                evidence["energy_note"] = energy_note

            if tool_name == "semantic_search":
                sim = row.get("similarity")
                if sim is not None:
                    citations.append(f"semantic_search.similarity={sim}")
                    evidence["similarity"] = float(cast(float, sim))
                if genre:
                    citations.append(f"semantic_search.genre={genre}")
            elif tool_name == "hybrid_recommend":
                score = row.get("score")
                sources = row.get("sources")
                sem_sim = row.get("semantic_similarity")
                if score is not None:
                    citations.append(f"hybrid_recommend.score={score}")
                    evidence["hybrid_score"] = float(cast(float, score))
                if sem_sim is not None:
                    evidence["semantic_similarity"] = float(cast(float, sem_sim))
                sources_list = _as_list(sources)
                if sources_list:
                    source_names = [
                        str(source)
                        for source in sources_list[:_TOOL_RESULTS_PROMPT_MAX_SOURCES]
                    ]
                    joined_sources = ",".join(source_names)
                    citations.append(f"hybrid_recommend.sources={joined_sources}")
                    evidence["sources"] = source_names

            seed_row: dict[str, object] = {
                "id": rec_id,
                "name": name,
                "reason": "",
                "citations": citations,
            }
            if evidence:
                seed_row["evidence"] = evidence

            # Extract score from evidence for top-level access
            if "similarity" in evidence:
                seed_row["score"] = evidence["similarity"]
            elif "hybrid_score" in evidence:
                seed_row["score"] = evidence["hybrid_score"]

            is_playable = row.get("is_playable")
            audio_url = row.get("audio_url")
            if is_playable is not None:
                seed_row["is_playable"] = is_playable
            if audio_url is not None:
                seed_row["audio_url"] = audio_url

            seed_rows.append(seed_row)

        total = len(seed_rows)
        for idx, row in enumerate(seed_rows):
            raw_score = row.get("score")
            raw_float = (
                float(cast(float, raw_score))
                if isinstance(raw_score, (int, float))
                else None
            )
            row["display_score"] = _calibrate_display_score(raw_float, idx, total)

        return seed_rows

    def _generate_final_response(
        self,
        state: SessionState,
        intent_slots: dict[str, object],
        query_text: str,
        rag_context: str,
        tool_results: list[dict[str, object]],
        seed_recommendations: list[dict[str, object]],
        tool_failures: list[str],
    ) -> dict[str, object]:
        compact_slots: dict[str, object] = {}
        for key, value in intent_slots.items():
            if key == _SLOT_QUERY_TEXT:
                continue
            if isinstance(value, str):
                text_value = value.strip()
                if text_value:
                    compact_slots[key] = text_value
                continue
            if value is not None:
                compact_slots[key] = value

        payload: dict[str, object] = {
            "intent": _as_text(intent_slots.get(_SLOT_INTENT)),
            "slots": compact_slots,
            "query_text": query_text,
        }
        if rag_context:
            payload["rag_context"] = rag_context

        summarized_tools = self._summarize_tool_results_for_prompt(tool_results)
        if summarized_tools:
            payload["tool_results"] = summarized_tools

        if tool_failures:
            payload["tool_failures"] = tool_failures

        recs_for_prompt: list[dict[str, object]] = []
        for r in seed_recommendations:
            rec_data: dict[str, object] = {
                "id": r["id"],
                "name": r["name"],
            }
            evidence = r.get("evidence", {})
            if evidence:
                rec_data["evidence"] = evidence
            recs_for_prompt.append(rec_data)

        payload["recommendations"] = recs_for_prompt

        user_context: dict[str, object] = {}
        if state.current_mood:
            user_context["mood"] = state.current_mood
        if state.current_scene:
            user_context["scene"] = state.current_scene
        if state.current_genre:
            user_context["genre"] = state.current_genre
        if state.preference_profile.preferred_energy:
            user_context["energy"] = state.preference_profile.preferred_energy
        if state.preference_profile.preferred_vocals:
            user_context["vocals"] = state.preference_profile.preferred_vocals
        if user_context:
            payload["user_context"] = user_context

        # Add multi-turn context for explanation generation
        multi_turn_context: dict[str, object] = {}
        if state.liked_songs:
            multi_turn_context["liked_count"] = len(state.liked_songs)
        if state.disliked_songs:
            multi_turn_context["disliked_count"] = len(state.disliked_songs)
        if state.exclude_ids:
            multi_turn_context["excluded_count"] = len(state.exclude_ids)
        if state.recommendation_history:
            multi_turn_context["previous_recommendation_rounds"] = len(
                state.recommendation_history
            )
        if multi_turn_context:
            payload["multi_turn_context"] = multi_turn_context

        prompt = (
            "Return ONLY valid JSON with fields: assistant_text, recommendations.\n"
            "Rules:\n"
            "- assistant_text: brief natural language (1-2 sentences in Chinese)\n"
            "- recommendations: array with id, name, reason, citations\n"
            "- reason: REQUIRED. Write 15-40 Chinese characters explaining WHY this song fits user.\n"
            "- You MUST use evidence from: genre_description, mood_tags, scene_tags, instrumentation, energy_note\n"
            "- Each reason MUST mention at least ONE specific musical characteristic (NOT just genre name)\n"
            "- DO NOT mention: similarity score, embedding, ranking, algorithm, technical terms\n"
            "- DO NOT use generic phrases like '适合你的场景' or '符合你的需求'\n"
            "- Good examples (with musical specifics):\n"
            "  * '弱化节奏推进，合成器铺陈出沉浸感，适合深夜独处'\n"
            "  * '钢琴与弦乐交织，旋律宁静深远，适合安静思考'\n"
            "  * '低保真采样带有温暖噪点，节奏松散，适合专注陪伴'\n"
            "  * '爵士和声变化丰富，即兴段落有格调，适合轻松氛围'\n"
            "- Bad examples (too generic, DO NOT USE):\n"
            "  * '适合学习'\n"
            "  * '旋律好听'\n"
            "  * '这首歌很适合你'\n"
            "- Use double quotes, no markdown, no code fences\n\n"
            f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
        )

        try:
            response = self.llm.chat(
                messages=self._build_messages(state, prompt),
                temperature=0.2,
                max_tokens=600,
                json_output=True,
            )
            parsed = self._parse_chat_json(response)
            if parsed is None:
                logger.warning(
                    "Failed to parse LLM final response JSON, generating fallback response"
                )
                return self._build_fallback_response(
                    state,
                    query_text,
                    seed_recommendations,
                    user_context,
                    multi_turn_context,
                )

            assistant_text = _as_text(parsed.get(_FINAL_ASSISTANT_TEXT))
            validated_recommendations = self._validate_final_recommendations(
                parsed.get(_FINAL_RECOMMENDATIONS),
                seed_recommendations,
            )
            result: dict[str, object] = {
                _FINAL_ASSISTANT_TEXT: assistant_text,
                _FINAL_RECOMMENDATIONS: validated_recommendations,
            }
            followup = _as_text(parsed.get(_FINAL_FOLLOWUP))
            if followup:
                result[_FINAL_FOLLOWUP] = followup
            return result
        except Exception as e:
            logger.error(f"Exception in _generate_final_response: {e}", exc_info=True)
            state.llm_status = "fallback"
            return self._build_fallback_response(
                state,
                query_text,
                seed_recommendations,
                user_context,
                multi_turn_context,
            )

    def _build_fallback_response(
        self,
        state: SessionState,
        query_text: str,
        seed_recommendations: list[dict[str, object]],
        user_context: dict[str, object],
        multi_turn_context: dict[str, object],
    ) -> dict[str, object]:
        """Generate a natural fallback response when LLM JSON parsing fails."""
        import hashlib

        parts: list[str] = []

        if user_context:
            context_parts = []
            if user_context.get("mood"):
                context_parts.append(f"你提到的{user_context['mood']}心情")
            if user_context.get("scene"):
                context_parts.append(f"{user_context['scene']}场景")
            if user_context.get("energy"):
                energy_map = {"low": "安静", "medium": "适中", "high": "高能量"}
                context_parts.append(
                    f"{energy_map.get(str(user_context['energy']), str(user_context['energy']))}风格"
                )
            if context_parts:
                parts.append(f"基于{', '.join(context_parts[:2])}，")

        parts.append(f"为你找到了 {len(seed_recommendations)} 首歌曲推荐。")

        excluded_count = multi_turn_context.get("excluded_count")
        if (
            excluded_count
            and isinstance(excluded_count, (int, float))
            and excluded_count > 0
        ):
            parts.append("已避开你之前反馈过的内容。")

        prev_rounds = multi_turn_context.get("previous_recommendation_rounds")
        if prev_rounds and isinstance(prev_rounds, (int, float)) and prev_rounds > 0:
            parts.append("这是基于你当前偏好的新一轮推荐。")

        _DEFAULT_REASONS = [
            "旋律与你的需求相匹配",
            "风格适合当前场景",
            "节奏和氛围都很合适",
            "这首作品值得一听",
            "符合你提到的音乐偏好",
        ]

        enhanced_recommendations = []
        for rec in seed_recommendations:
            enhanced_rec = dict(rec)
            rec_id = str(rec.get("id", ""))

            if not rec.get("reason"):
                evidence = rec.get("evidence")
                genre = ""
                title = ""
                artist = ""
                similarity = None
                sources = None
                if isinstance(evidence, dict):
                    genre = str(evidence.get("genre") or "")
                    title = str(evidence.get("title") or "")
                    artist = str(evidence.get("artist") or "")
                    similarity = evidence.get("similarity")
                    sources = evidence.get("sources")

                reason_parts = []

                if user_context:
                    if user_context.get("scene"):
                        reason_parts.append(f"适合{user_context['scene']}场景")
                    if user_context.get("mood"):
                        reason_parts.append(f"符合{user_context['mood']}心情")
                    if user_context.get("genre"):
                        reason_parts.append(f"{user_context['genre']}风格")
                    if user_context.get("energy"):
                        energy_desc = {
                            "low": "轻松舒缓",
                            "medium": "节奏适中",
                            "high": "活力十足",
                        }
                        energy_text = energy_desc.get(str(user_context["energy"]), "")
                        if energy_text:
                            reason_parts.append(energy_text)

                if len(reason_parts) < 2:
                    if artist and artist not in "，".join(reason_parts):
                        reason_parts.append(f"来自{artist}")
                    if genre and genre not in "，".join(reason_parts):
                        reason_parts.append(f"{genre}风格")

                prev_rounds_value = multi_turn_context.get(
                    "previous_recommendation_rounds", 0
                )
                if (
                    isinstance(prev_rounds_value, (int, float))
                    and prev_rounds_value > 0
                ):
                    if len(reason_parts) < 3:
                        reason_parts.append("基于你的偏好调整")

                if sources and isinstance(sources, list):
                    if "semantic" in sources and similarity is not None:
                        if similarity > 0.35:
                            reason_parts.append("很契合你的描述")
                        elif similarity > 0.26:
                            reason_parts.append("与你的需求相关")

                if reason_parts:
                    enhanced_rec["reason"] = "，".join([p for p in reason_parts if p])
                else:
                    if rec_id:
                        idx = int(hashlib.md5(rec_id.encode()).hexdigest(), 16) % len(
                            _DEFAULT_REASONS
                        )
                        enhanced_rec["reason"] = _DEFAULT_REASONS[idx]
                    else:
                        enhanced_rec["reason"] = "根据你的听歌偏好推荐"
            else:
                if not enhanced_rec.get("reason"):
                    if rec_id:
                        idx = int(hashlib.md5(rec_id.encode()).hexdigest(), 16) % len(
                            _DEFAULT_REASONS
                        )
                        enhanced_rec["reason"] = _DEFAULT_REASONS[idx]
                    else:
                        enhanced_rec["reason"] = "根据你的听歌偏好推荐"

            if rec.get("is_playable") is not None:
                enhanced_rec["is_playable"] = rec["is_playable"]
            if rec.get("audio_url") is not None:
                enhanced_rec["audio_url"] = rec["audio_url"]

            enhanced_recommendations.append(enhanced_rec)

        return {
            _FINAL_ASSISTANT_TEXT: " ".join(parts),
            _FINAL_RECOMMENDATIONS: enhanced_recommendations,
        }

    @staticmethod
    def _validate_final_recommendations(
        generated: object,
        seed_recommendations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        allowed_by_id: dict[str, dict[str, object]] = {}
        for row in seed_recommendations:
            rec_id = _as_text(row.get("id"))
            if rec_id:
                allowed_by_id[rec_id] = row

        generated_rows = _as_list(generated)
        if generated_rows is None:
            return Orchestrator._ensure_reasons(seed_recommendations)

        validated: list[dict[str, object]] = []
        for item_obj in generated_rows:
            item = _as_dict(item_obj)
            if item is None:
                continue
            rec_id = _as_text(item.get("id"))
            if not rec_id or rec_id not in allowed_by_id:
                continue

            seed = allowed_by_id[rec_id]
            name = _as_text(seed.get("name"))

            llm_reason = _as_text(item.get("reason"))
            seed_reason = _as_text(seed.get("reason"))
            reason = (
                llm_reason
                if llm_reason and len(llm_reason) > 5
                else (seed_reason if seed_reason else "")
            )

            citations_raw = _as_list(item.get("citations"))
            citations: list[str] = []
            if citations_raw is not None:
                for citation_obj in citations_raw:
                    citation = _as_text(citation_obj)
                    if citation:
                        citations.append(citation)
            if not citations:
                seed_citations_raw = _as_list(seed.get("citations")) or ["tool_output"]
                for citation_obj in seed_citations_raw:
                    citation = _as_text(citation_obj)
                    if citation:
                        citations.append(citation)
            if not citations:
                citations = ["tool_output"]

            result: dict[str, object] = {
                "id": rec_id,
                "name": name or rec_id,
                "reason": reason,
                "citations": citations,
            }

            if seed.get("is_playable") is not None:
                result["is_playable"] = seed["is_playable"]
            if seed.get("audio_url") is not None:
                result["audio_url"] = seed["audio_url"]
            if seed.get("score") is not None:
                result["score"] = seed["score"]
            if seed.get("display_score") is not None:
                result["display_score"] = seed["display_score"]

            validated.append(result)

        if validated:
            return validated
        return Orchestrator._ensure_reasons(seed_recommendations)

    @staticmethod
    def _ensure_reasons(
        recommendations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        import hashlib

        _NATURAL_REASON_TEMPLATES = [
            "这首歌的旋律很适合你当前的需求",
            "节奏和氛围都很贴合你的偏好",
            "风格上与你的听歌习惯相契合",
            "这首作品值得一听，很有特点",
            "整体感觉很适合你现在的场景",
            "曲风和情绪都很到位",
            "旋律线条很舒服，值得一试",
            "这首歌的氛围感很好",
            "节奏编排得很有层次感",
            "编曲和你的口味很匹配",
        ]

        _ARTIST_TEMPLATES = [
            "来自{artist}的作品",
            "{artist}的演绎很有感染力",
            "这首歌展现了{artist}的独特风格",
            "{artist}的音乐表达很到位",
        ]

        _GENRE_TEMPLATES = [
            "{genre}风格的佳作",
            "很有{genre}的味道",
            "典型的{genre}风格呈现",
            "{genre}元素的精彩演绎",
        ]

        result: list[dict[str, object]] = []
        for rec in recommendations:
            enhanced = dict(rec)
            existing_reason = _as_text(rec.get("reason"))
            if existing_reason and len(existing_reason) > 5:
                enhanced["reason"] = existing_reason
            else:
                rec_id = str(rec.get("id", ""))
                evidence = rec.get("evidence")
                name = str(rec.get("name", ""))

                genre = ""
                artist = ""
                if isinstance(evidence, dict):
                    genre = str(evidence.get("genre") or "")
                    artist = str(evidence.get("artist") or "")
                    if " - " in name and not artist:
                        artist = name.split(" - ")[0].strip()

                rec_hash = (
                    int(hashlib.md5(rec_id.encode()).hexdigest(), 16) if rec_id else 0
                )

                if genre and artist:
                    template_idx = rec_hash % len(_ARTIST_TEMPLATES)
                    reason = _ARTIST_TEMPLATES[template_idx].format(artist=artist)
                elif artist:
                    template_idx = rec_hash % len(_ARTIST_TEMPLATES)
                    reason = _ARTIST_TEMPLATES[template_idx].format(artist=artist)
                elif genre:
                    template_idx = rec_hash % len(_GENRE_TEMPLATES)
                    reason = _GENRE_TEMPLATES[template_idx].format(genre=genre)
                else:
                    template_idx = rec_hash % len(_NATURAL_REASON_TEMPLATES)
                    reason = _NATURAL_REASON_TEMPLATES[template_idx]

                enhanced["reason"] = reason

            result.append(enhanced)

        return result

    @staticmethod
    def _fallback_reply(
        user_text: str,
        intent_slots: dict[str, object],
        recommendations: list[dict[str, object]],
        tool_failures: list[str],
    ) -> str:
        if recommendations:
            preview = "、".join(
                _as_text(row.get("name")) for row in recommendations[:3]
            )
            return f"我找到了 {len(recommendations)} 首相关歌曲：{preview}。如果你愿意，我可以继续细化。"

        intent = _as_text(intent_slots.get(_SLOT_INTENT))
        if intent == _INTENT_FEEDBACK:
            return "收到你的反馈，我会据此调整后续推荐。"

        if tool_failures:
            return f"这次检索遇到问题（{tool_failures[0]}）。你可以换个关键词，我继续帮你找。"

        if user_text:
            return "我已记录你的需求。你可以补充一个场景、情绪或歌手，我继续帮你推荐。"
        return "告诉我你想听什么类型的音乐，我来帮你推荐。"

    @staticmethod
    def _build_entities(intent_slots: dict[str, object]) -> dict[str, object]:
        entities: dict[str, object] = {}
        for key in (
            _SLOT_MOOD,
            _SLOT_SCENE,
            _SLOT_GENRE,
            _SLOT_ARTIST,
            _SLOT_SONG_NAME,
            _SLOT_ENERGY,
            _SLOT_VOCALS,
            _SLOT_FEEDBACK,
        ):
            value = intent_slots.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            entities[key] = value
        return entities
