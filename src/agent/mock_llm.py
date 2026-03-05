from __future__ import annotations

import json
import re
from typing import cast

from typing_extensions import override

from src.llm.clients.base import BaseLLMClient, ChatResponse

_INTENT_RECOMMEND = "recommend_music"
_INTENT_SEARCH = "search_music"
_INTENT_REFINE = "refine_preferences"
_INTENT_EXPLAIN = "explain_why"
_INTENT_FEEDBACK = "feedback"


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


class MockLLMClient(BaseLLMClient):
    @override
    def chat(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_output: bool = False,
        stream: bool = False,
    ) -> ChatResponse:
        _ = tools
        _ = temperature
        _ = max_tokens
        _ = json_output
        _ = stream

        validated_messages = self.validate_messages(messages)
        user_content = self._last_user_message(validated_messages)

        if "INTENT_AND_SLOTS_SCHEMA" in user_content:
            payload = self._extract_payload(user_content)
            user_text = _as_text(payload.get("user_text"))
            data = self._mock_intent_and_slots(user_text)
            content = json.dumps(data, ensure_ascii=False)
            return ChatResponse(content=content, json_data=data, raw={"stage": "intent"})

        if "FINAL_RESPONSE_SCHEMA" in user_content:
            payload = self._extract_payload(user_content)
            data = self._mock_final_response(payload)
            content = json.dumps(data, ensure_ascii=False)
            return ChatResponse(content=content, json_data=data, raw={"stage": "final"})

        fallback_recommendations: list[object] = []
        fallback: dict[str, object] = {
            "assistant_text": "我在。告诉我你想听什么风格的音乐吧。",
            "recommendations": fallback_recommendations,
            "followup_question": "你现在更偏好哪种情绪或场景？",
        }
        fallback_content = json.dumps(fallback, ensure_ascii=False)
        return ChatResponse(content=fallback_content, json_data=fallback, raw={"stage": "fallback"})

    @staticmethod
    def _last_user_message(messages: list[dict[str, object]]) -> str:
        for message in reversed(messages):
            role = _as_text(message.get("role"))
            if role == "user":
                return _as_text(message.get("content"))
        return ""

    @staticmethod
    def _extract_payload(content: str) -> dict[str, object]:
        start = content.find("{")
        if start < 0:
            return {}
        candidate = content[start:]
        try:
            parsed_obj = cast(object, json.loads(candidate))
        except json.JSONDecodeError:
            return {}
        parsed_dict = _as_dict(parsed_obj)
        if parsed_dict is None:
            return {}
        return parsed_dict

    def _mock_intent_and_slots(self, user_text: str) -> dict[str, object]:
        text = user_text.strip()
        lowered = text.lower()

        intent = _INTENT_SEARCH
        if any(token in lowered for token in ("为什么", "理由", "explain")):
            intent = _INTENT_EXPLAIN
        elif any(token in lowered for token in ("不喜欢", "跳过", "dislike", "skip", "like", "喜欢")):
            intent = _INTENT_FEEDBACK
        elif any(token in lowered for token in ("换", "再来", "调整", "refine")):
            intent = _INTENT_REFINE
        elif any(token in lowered for token in ("推荐", "来点", "听点", "recommend")):
            intent = _INTENT_RECOMMEND

        top_k = 5
        top_k_match = re.search(r"(\d{1,2})\s*首", text)
        if top_k_match:
            top_k = _clamp_top_k(top_k_match.group(1), default=5)

        result: dict[str, object] = {
            "intent": intent,
            "query_text": text or "推荐音乐",
            "top_k": top_k,
        }

        mood = self._extract_mood(text)
        if mood:
            result["mood"] = mood

        scene = self._extract_scene(text)
        if scene:
            result["scene"] = scene

        song_name = self._extract_song_name(text)
        if song_name:
            result["song_name"] = song_name

        if intent == _INTENT_FEEDBACK:
            feedback = self._extract_feedback(text)
            if feedback:
                result["feedback"] = feedback

        return result

    @staticmethod
    def _extract_mood(text: str) -> str | None:
        mood_map: list[tuple[str, str]] = [
            ("放松", "放松"),
            ("平静", "平静"),
            ("开心", "开心"),
            ("伤心", "伤感"),
            ("治愈", "治愈"),
            ("兴奋", "兴奋"),
        ]
        for keyword, normalized in mood_map:
            if keyword in text:
                return normalized
        return None

    @staticmethod
    def _extract_scene(text: str) -> str | None:
        scene_map: list[tuple[str, str]] = [
            ("学习", "学习"),
            ("工作", "工作"),
            ("跑步", "跑步"),
            ("运动", "运动"),
            ("健身", "运动"),
            ("睡前", "睡前"),
            ("通勤", "通勤"),
            ("开车", "通勤"),
        ]
        for keyword, normalized in scene_map:
            if keyword in text:
                return normalized
        return None

    @staticmethod
    def _extract_song_name(text: str) -> str | None:
        title_match = re.search(r"《([^》]+)》", text)
        if title_match:
            name = title_match.group(1).strip()
            if name:
                return name

        quote_match = re.search(r"\"([^\"]+)\"", text)
        if quote_match:
            name = quote_match.group(1).strip()
            if name:
                return name

        return None

    @staticmethod
    def _extract_feedback(text: str) -> dict[str, str] | None:
        lowered = text.lower()
        feedback_type = ""
        if "不喜欢" in text or "dislike" in lowered:
            feedback_type = "dislike"
        elif "跳过" in text or "skip" in lowered:
            feedback_type = "skip"
        elif "喜欢" in text or "like" in lowered:
            feedback_type = "like"

        if not feedback_type:
            return None

        feedback: dict[str, str] = {"type": feedback_type}
        target_match = re.search(r"(?:id[:：\s]*)([A-Za-z0-9_\-]+)", text, re.IGNORECASE)
        if target_match:
            target_id = target_match.group(1).strip()
            if target_id:
                feedback["target_id"] = target_id
        return feedback

    @staticmethod
    def _mock_final_response(payload: dict[str, object]) -> dict[str, object]:
        recommendations_raw = _as_list(payload.get("recommendations")) or []

        recommendations: list[dict[str, object]] = []
        for item_raw in recommendations_raw:
            item = _as_dict(item_raw)
            if item is None:
                continue

            rec_id = _as_text(item.get("id"))
            name = _as_text(item.get("name"))
            if not rec_id or not name:
                continue

            reason = _as_text(item.get("reason")) or "与当前需求匹配"
            citations_raw = _as_list(item.get("citations")) or ["tool_output"]
            citations: list[str] = []
            for citation_obj in citations_raw:
                citation = _as_text(citation_obj)
                if citation:
                    citations.append(citation)
            if not citations:
                citations.append("tool_output")

            recommendations.append(
                {
                    "id": rec_id,
                    "name": name,
                    "reason": reason,
                    "citations": citations,
                }
            )

        tool_failures_raw = _as_list(payload.get("tool_failures")) or []
        tool_failures: list[str] = []
        for error_obj in tool_failures_raw:
            error_text = _as_text(error_obj)
            if error_text:
                tool_failures.append(error_text)

        if recommendations:
            assistant_text = f"我根据你的需求整理了 {len(recommendations)} 首歌，先听听看。"
        elif tool_failures:
            assistant_text = "工具这次没有成功返回结果，我先记录你的需求，你可以换个关键词再试。"
        else:
            assistant_text = "我还没有拿到可用的推荐结果，你可以补充一个情绪或场景。"

        return {
            "assistant_text": assistant_text,
            "recommendations": recommendations,
            "followup_question": "你想要更放松一点，还是更有节奏一点？",
        }
