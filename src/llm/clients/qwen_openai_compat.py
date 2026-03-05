import importlib
import json
import logging
import os
from collections.abc import Sequence
from typing import Protocol, cast

from .base import BaseLLMClient, ChatResponse, ToolCall


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus")


class _CompletionCreateProtocol(Protocol):
    def create(self, **kwargs: object) -> object: ...


class _ChatCompletionsProtocol(Protocol):
    completions: _CompletionCreateProtocol


class _OpenAIClientProtocol(Protocol):
    chat: _ChatCompletionsProtocol


class _OpenAIConstructor(Protocol):
    def __call__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
    ) -> _OpenAIClientProtocol: ...


class QwenClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        self.api_key: str | None = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model: str = model
        self.base_url: str = base_url
        self.timeout: float = timeout
        self._client: _OpenAIClientProtocol | None = None

    def _get_client(self) -> _OpenAIClientProtocol:
        if not self.api_key:
            raise EnvironmentError(
                "缺少 DASHSCOPE_API_KEY。请先设置环境变量 DASHSCOPE_API_KEY。"
            )

        if self._client is None:
            try:
                openai_module = importlib.import_module("openai")
            except ImportError as exc:
                raise ImportError(
                    "openai 未安装。请运行: pip install openai"
                ) from exc

            openai_cls_obj = getattr(openai_module, "OpenAI", None)
            if openai_cls_obj is None:
                raise ImportError("openai 模块不包含 OpenAI 客户端。")

            openai_cls = cast(_OpenAIConstructor, openai_cls_obj)
            created_client = openai_cls(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            self._client = created_client

        return self._client

    @staticmethod
    def _as_dict(value: object, name: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a dict.")
        return cast(dict[str, object], value)

    @staticmethod
    def _as_list(value: object, name: str) -> list[object]:
        if not isinstance(value, list):
            raise ValueError(f"{name} must be a list.")
        return cast(list[object], value)

    def _prepare_messages(
        self,
        messages: list[dict[str, object]],
        json_output: bool,
    ) -> list[dict[str, object]]:
        request_messages = [dict(message) for message in messages]

        if not json_output:
            return request_messages

        instruction = (
            "Return strict JSON only. "
            "Do not include markdown, code fences, or extra commentary."
        )

        if request_messages and request_messages[0].get("role") == "system":
            system_content = str(request_messages[0].get("content") or "").strip()
            request_messages[0]["content"] = (
                f"{system_content}\n\n{instruction}" if system_content else instruction
            )
        else:
            request_messages.insert(0, {"role": "system", "content": instruction})

        return request_messages

    def _create_completion(
        self,
        messages: list[dict[str, object]],
        tools: Sequence[dict[str, object]] | None,
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = list(tools)
            if stream:
                logger.warning("tools provided; forcing stream=False for compatibility")
            payload["stream"] = False

        completion_obj = self._get_client().chat.completions.create(**payload)
        model_dump_attr = getattr(completion_obj, "model_dump", None)
        if not callable(model_dump_attr):
            raise ValueError("Unexpected OpenAI-compatible response format.")

        dumped = model_dump_attr()
        return self._as_dict(dumped, "completion")

    def _extract_tool_calls(self, message_dict: dict[str, object]) -> list[ToolCall]:
        raw_tool_calls = message_dict.get("tool_calls")
        if raw_tool_calls is None:
            return []

        tool_call_items = self._as_list(raw_tool_calls, "message.tool_calls")
        parsed_tool_calls: list[ToolCall] = []

        for idx, item in enumerate(tool_call_items):
            item_dict = self._as_dict(item, f"message.tool_calls[{idx}]")
            function_dict = self._as_dict(item_dict.get("function") or {}, "tool_call.function")

            parsed_tool_calls.append(
                ToolCall(
                    id=str(item_dict.get("id") or ""),
                    name=str(function_dict.get("name") or ""),
                    arguments=str(function_dict.get("arguments") or "{}"),
                )
            )

        return parsed_tool_calls

    def _parse_json_or_retry_once(
        self,
        request_messages: list[dict[str, object]],
        content: str,
        temperature: float,
        max_tokens: int | None,
    ) -> tuple[object, str]:
        try:
            return json.loads(content), content
        except json.JSONDecodeError:
            assistant_message: dict[str, object] = {"role": "assistant", "content": content}
            repair_instruction: dict[str, object] = {"role": "user", "content": "repair JSON only"}
            repair_messages = [
                *request_messages,
                assistant_message,
                repair_instruction,
            ]
            repair_completion = self._create_completion(
                messages=repair_messages,
                tools=None,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            choices = self._as_list(repair_completion.get("choices"), "completion.choices")
            if not choices:
                raise ValueError("Model returned no choices while repairing JSON.")

            repair_choice = self._as_dict(choices[0], "completion.choices[0]")
            repair_message = self._as_dict(repair_choice.get("message") or {}, "choice.message")
            repaired_content = str(repair_message.get("content") or "")

            try:
                return json.loads(repaired_content), repaired_content
            except json.JSONDecodeError as exc:
                raise ValueError("JSON parsing failed after one repair attempt.") from exc

    def chat(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        json_output: bool = False,
        stream: bool = False,
    ) -> ChatResponse:
        validated_messages = self.validate_messages(messages)
        request_messages = self._prepare_messages(validated_messages, json_output=json_output)

        completion = self._create_completion(
            messages=request_messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        choices = self._as_list(completion.get("choices"), "completion.choices")
        if not choices:
            raise ValueError("Model returned no choices.")

        choice = self._as_dict(choices[0], "completion.choices[0]")
        message = self._as_dict(choice.get("message") or {}, "choice.message")

        content = str(message.get("content") or "")
        tool_calls = self._extract_tool_calls(message)

        response = ChatResponse(
            content=content,
            tool_calls=tool_calls,
            raw=completion,
        )

        if json_output:
            parsed_json, final_content = self._parse_json_or_retry_once(
                request_messages=request_messages,
                content=content,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response.content = final_content
            response.json_data = parsed_json

        return response
