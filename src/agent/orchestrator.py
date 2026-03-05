from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter, ValidationError

from src.llm.clients.base import BaseLLMClient, ChatResponse
from src.llm.prompts.schemas import FINAL_RESPONSE_SCHEMA, INTENT_AND_SLOTS_SCHEMA
from src.manager.session_state import SessionState
from src.rag.context_builder import build_rag_context
from src.rag.retriever import retrieve_semantic_docs
from src.rag.sanitize import sanitize_untrusted_text
from src.tools.registry import ToolRegistry

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
_SLOT_TOP_K = "top_k"
_SLOT_FEEDBACK = "feedback"

_FEEDBACK_TYPE = "type"
_FEEDBACK_TARGET_ID = "target_id"

_FINAL_ASSISTANT_TEXT = "assistant_text"
_FINAL_RECOMMENDATIONS = "recommendations"
_FINAL_FOLLOWUP = "followup_question"

_INTENT_PROPERTIES = cast(dict[str, object], INTENT_AND_SLOTS_SCHEMA.get("properties", {}))
_FINAL_PROPERTIES = cast(dict[str, object], FINAL_RESPONSE_SCHEMA.get("properties", {}))

if _SLOT_INTENT not in _INTENT_PROPERTIES or _SLOT_QUERY_TEXT not in _INTENT_PROPERTIES:
    raise ValueError("INTENT_AND_SLOTS_SCHEMA is missing required keys.")
if _FINAL_ASSISTANT_TEXT not in _FINAL_PROPERTIES or _FINAL_RECOMMENDATIONS not in _FINAL_PROPERTIES:
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
            else Path(__file__).resolve().parent.parent / "llm" / "prompts" / "system_prompt.txt"
        )
        self.system_prompt: str = prompt_path.read_text(encoding="utf-8").strip()

    def handle_turn(self, user_text: str, state: SessionState) -> str:
        text = user_text.strip()
        if not text:
            reply = "请告诉我你想听什么类型的音乐，我可以马上帮你找。"
            state.add_dialogue_turn(user_input=user_text, system_response=reply, intent=None, entities={})
            return reply

        intent_slots = self._extract_intent_and_slots(text, state)
        intent = _as_text(intent_slots.get(_SLOT_INTENT)) or _INTENT_SEARCH
        query_text = _as_text(intent_slots.get(_SLOT_QUERY_TEXT)) or text
        top_k = _clamp_top_k(intent_slots.get(_SLOT_TOP_K), default=5)

        mood = _as_text(intent_slots.get(_SLOT_MOOD))
        if mood:
            state.update_mood(mood)

        scene = _as_text(intent_slots.get(_SLOT_SCENE))
        if scene:
            state.update_scene(scene)

        if intent == _INTENT_FEEDBACK:
            self._apply_feedback(intent_slots, state)

        tool_plan = self._build_tool_plan(intent, intent_slots, query_text, top_k)
        tool_results = self._dispatch_tools(tool_plan)

        rag_context = self._build_rag_context(query_text, top_k)
        recommendations, method = self._extract_recommendations(tool_results)

        if recommendations and method is not None:
            state.add_recommendation(
                query=query_text,
                results=[item["id"] for item in recommendations],
                method=method,
            )

        reply = self._compose_reply(
            user_text=text,
            state=state,
            intent_slots=intent_slots,
            query_text=query_text,
            rag_context=rag_context,
            tool_results=tool_results,
            recommendations=recommendations,
        )

        entities = self._build_entities(intent_slots)
        state.add_dialogue_turn(
            user_input=user_text,
            system_response=reply,
            intent=intent,
            entities=entities,
        )
        return reply

    def _extract_intent_and_slots(self, user_text: str, state: SessionState) -> dict[str, object]:
        payload: dict[str, object] = {
            "user_text": user_text,
            "context": state.get_context_summary(),
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
            pass

        return self._deterministic_intent_slots(user_text, state)

    def _build_messages(self, state: SessionState, current_user_prompt: str) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = [{"role": "system", "content": self.system_prompt}]
        for turn in state.dialogue_history:
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

        for key in (_SLOT_MOOD, _SLOT_SCENE, _SLOT_GENRE, _SLOT_ARTIST, _SLOT_SONG_NAME):
            value = _as_text(payload.get(key))
            if value:
                result[key] = value

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

    def _deterministic_intent_slots(self, user_text: str, state: SessionState) -> dict[str, object]:
        lowered = user_text.lower()

        intent = _INTENT_SEARCH
        if any(token in lowered for token in ("为什么", "理由", "explain")):
            intent = _INTENT_EXPLAIN
        elif any(token in lowered for token in ("不喜欢", "跳过", "dislike", "skip", "like", "喜欢")):
            intent = _INTENT_FEEDBACK
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
    def _extract_feedback(user_text: str, state: SessionState) -> dict[str, object] | None:
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

        target_match = re.search(r"(?:id[:：\s]*)([A-Za-z0-9_\-]+)", user_text, re.IGNORECASE)
        target_id = target_match.group(1).strip() if target_match else ""
        if not target_id and state.last_recommendation is not None and state.last_recommendation.results:
            target_id = state.last_recommendation.results[0]

        feedback: dict[str, object] = {_FEEDBACK_TYPE: feedback_type}
        if target_id:
            feedback[_FEEDBACK_TARGET_ID] = target_id
        return feedback

    def _apply_feedback(self, intent_slots: dict[str, object], state: SessionState) -> None:
        feedback_obj = _as_dict(intent_slots.get(_SLOT_FEEDBACK))
        if feedback_obj is None:
            feedback_obj = self._extract_feedback(_as_text(intent_slots.get(_SLOT_QUERY_TEXT)), state)
            if feedback_obj is None:
                return

        feedback_type = _as_text(feedback_obj.get(_FEEDBACK_TYPE))
        if feedback_type not in {"like", "dislike", "skip"}:
            return

        target_id = _as_text(feedback_obj.get(_FEEDBACK_TARGET_ID))
        if not target_id and state.last_recommendation is not None and state.last_recommendation.results:
            target_id = state.last_recommendation.results[0]
        if not target_id:
            return

        state.add_feedback(target_id, feedback_type)

    def _build_tool_plan(
        self,
        intent: str,
        intent_slots: dict[str, object],
        query_text: str,
        top_k: int,
    ) -> list[tuple[str, dict[str, object]]]:
        if self.max_tool_calls <= 0:
            return []

        song_name = _as_text(intent_slots.get(_SLOT_SONG_NAME))
        if intent in {_INTENT_FEEDBACK, _INTENT_EXPLAIN}:
            return []

        if intent in {_INTENT_RECOMMEND, _INTENT_REFINE}:
            if song_name and query_text:
                return [
                    (
                        "hybrid_recommend",
                        {
                            "query_text": query_text,
                            "seed_song_name": song_name,
                            "top_k": top_k,
                            "w_sem": 0.6,
                            "w_cf": 0.4,
                        },
                    )
                ]
            if song_name:
                return [("cf_recommend", {"song_name": song_name, "top_k": top_k})]

        return [("semantic_search", {"query_text": query_text, "top_k": top_k})]

    def _dispatch_tools(self, tool_plan: list[tuple[str, dict[str, object]]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for tool_name, args in tool_plan[: self.max_tool_calls]:
            dispatch_result = self.tools.dispatch(tool_name, args)
            records.append({"name": tool_name, "args": args, "result": dispatch_result})
        return records

    def _build_rag_context(self, query_text: str, top_k: int) -> str:
        try:
            docs = retrieve_semantic_docs(query_text, top_k)
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

        return build_rag_context(safe_docs)

    def _extract_recommendations(
        self,
        tool_results: list[dict[str, object]],
    ) -> tuple[list[dict[str, str]], str | None]:
        method_map = {
            "semantic_search": "semantic",
            "cf_recommend": "collaborative",
            "hybrid_recommend": "hybrid",
        }

        for row in tool_results:
            tool_name = _as_text(row.get("name"))
            result = _as_dict(row.get("result"))
            if not tool_name or result is None:
                continue
            if result.get("ok") is not True:
                continue

            recommendations = self._extract_recommendations_for_tool(tool_name, result.get("data"))
            if not recommendations:
                continue

            method = method_map.get(tool_name)
            if method is None:
                continue
            return recommendations, method

        return [], None

    def _extract_recommendations_for_tool(self, tool_name: str, data: object) -> list[dict[str, str]]:
        if tool_name == "cf_recommend":
            payload = _as_dict(data)
            if payload is None:
                return []
            recommendations_raw = _as_list(payload.get("recommendations")) or []
            return self._build_recommendations_from_rows(recommendations_raw, use_cf_fields=True)

        rows = _as_list(data)
        if rows is None:
            return []
        return self._build_recommendations_from_rows(rows, use_cf_fields=False)

    @staticmethod
    def _build_recommendations_from_rows(
        rows: list[object],
        use_cf_fields: bool,
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
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
            results.append({"id": rec_id, "name": name})

        return results

    def _compose_reply(
        self,
        user_text: str,
        state: SessionState,
        intent_slots: dict[str, object],
        query_text: str,
        rag_context: str,
        tool_results: list[dict[str, object]],
        recommendations: list[dict[str, str]],
    ) -> str:
        tool_failures = self._collect_tool_failures(tool_results)
        if tool_results and len(tool_failures) == len(tool_results):
            error_text = tool_failures[0] if tool_failures else "工具调用失败"
            return f"抱歉，这次工具调用没有成功（{error_text}）。你可以换个关键词，我继续帮你找。"

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
        if assistant_text:
            if followup:
                return f"{assistant_text}\n{followup}"
            return assistant_text

        return self._fallback_reply(user_text, intent_slots, recommendations, tool_failures)

    def _collect_tool_failures(self, tool_results: list[dict[str, object]]) -> list[str]:
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
    def _build_seed_recommendations(recommendations: list[dict[str, str]]) -> list[dict[str, object]]:
        seed_rows: list[dict[str, object]] = []
        for row in recommendations:
            rec_id = _as_text(row.get("id"))
            name = _as_text(row.get("name"))
            if not rec_id or not name:
                continue
            seed_rows.append(
                {
                    "id": rec_id,
                    "name": name,
                    "reason": "与当前需求匹配",
                    "citations": ["tool_output"],
                }
            )
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
        payload: dict[str, object] = {
            "intent_slots": intent_slots,
            "query_text": query_text,
            "rag_context": rag_context,
            "tool_results": tool_results,
            "tool_failures": tool_failures,
            "recommendations": seed_recommendations,
            "schema": FINAL_RESPONSE_SCHEMA,
        }
        prompt = (
            "请基于 FINAL_RESPONSE_SCHEMA 输出严格 JSON。"
            "你只能使用已给出的 recommendations.id，不能创造新 ID。"
            "只返回 JSON 对象。\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
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
                return {
                    _FINAL_ASSISTANT_TEXT: "",
                    _FINAL_RECOMMENDATIONS: seed_recommendations,
                }

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
        except Exception:
            return {
                _FINAL_ASSISTANT_TEXT: "",
                _FINAL_RECOMMENDATIONS: seed_recommendations,
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
            return seed_recommendations

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
            reason = _as_text(item.get("reason")) or _as_text(seed.get("reason")) or "与你的需求匹配"

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

            validated.append(
                {
                    "id": rec_id,
                    "name": name or rec_id,
                    "reason": reason,
                    "citations": citations,
                }
            )

        if validated:
            return validated
        return seed_recommendations

    @staticmethod
    def _fallback_reply(
        user_text: str,
        intent_slots: dict[str, object],
        recommendations: list[dict[str, str]],
        tool_failures: list[str],
    ) -> str:
        if recommendations:
            preview = "、".join(row["name"] for row in recommendations[:3])
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
            _SLOT_FEEDBACK,
        ):
            value = intent_slots.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            entities[key] = value
        return entities
