import json
from abc import ABC, abstractmethod
from typing import cast

from pydantic import BaseModel, Field, TypeAdapter


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: str = "{}"

    def parsed_arguments(self) -> dict[str, object]:
        raw_arguments = (self.arguments or "").strip()
        if not raw_arguments:
            return {}
        try:
            return TypeAdapter(dict[str, object]).validate_json(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Tool call arguments must be valid JSON.") from exc


class ChatResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    json_data: object | None = None
    raw: dict[str, object] | None = None


class BaseLLMClient(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_output: bool = False,
        stream: bool = False,
    ) -> ChatResponse:
        raise NotImplementedError

    @staticmethod
    def validate_messages(messages: object) -> list[dict[str, object]]:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list of dicts.")

        raw_messages = cast(list[object], messages)
        validated: list[dict[str, object]] = []
        for idx, message in enumerate(raw_messages):
            if not isinstance(message, dict):
                raise TypeError("Each message must be a dict.")

            validated_message = cast(dict[str, object], message)

            role = validated_message.get("role")
            if role not in {"system", "user", "assistant", "tool"}:
                raise ValueError(f"Invalid message role at index {idx}: {role!r}")

            if role == "system" and idx != 0:
                raise ValueError("System message is only allowed at messages[0].")

            validated.append(validated_message)

        return validated
