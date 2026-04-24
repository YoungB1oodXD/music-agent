"""
Qwen 大模型客户端（OpenAI 兼容接口）

功能：
- 支持阿里云百炼普通接口和 Coding Plan 两种 API
- 自动从环境变量读取 API Key，支持优先级覆盖
- 提供详细的初始化日志和错误日志（脱敏处理）

环境变量优先级（从高到低）：
1. 显式传入的 api_key 参数
2. DASHSCOPE_API_KEY_BAILIAN（百炼普通接口 Key）
3. DASHSCOPE_API_KEY（Coding Plan Key，作为回退）

默认配置：
- base_url: https://dashscope.aliyuncs.com/compatible-mode/v1（百炼普通接口）
- model: qwen3.5-plus
- 可通过 DASHSCOPE_BASE_URL 和 DASHSCOPE_MODEL 环境变量覆盖

使用示例：
    # 使用百炼普通接口（推荐）
    export DASHSCOPE_API_KEY_BAILIAN="sk-xxx"
    client = QwenClient()  # 自动读取环境变量

    # 使用 Coding Plan
    export DASHSCOPE_API_KEY="your-coding-key"
    export DASHSCOPE_BASE_URL="https://coding.dashscope.aliyuncs.com/v1"
    client = QwenClient()
"""

import importlib
import json
import logging
import os
import time
from collections.abc import Sequence
from typing import Protocol, cast

from .base import BaseLLMClient, ChatResponse, ToolCall


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 默认使用百炼普通接口，可通过 DASHSCOPE_BASE_URL 覆盖
DEFAULT_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 默认模型，可通过 DASHSCOPE_MODEL 覆盖
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
    """
    Qwen 大模型客户端

    API Key 优先级：显式参数 > DASHSCOPE_API_KEY_BAILIAN > DASHSCOPE_API_KEY
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        # API Key 优先级：显式参数 > 百炼普通 Key > Coding Plan Key
        env_bailian_key = (os.getenv("DASHSCOPE_API_KEY_BAILIAN") or "").strip() or None
        env_coding_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip() or None
        explicit_key = (api_key or "").strip() or None
        self.api_key: str | None = explicit_key or env_bailian_key or env_coding_key
        self.model: str = model
        self.base_url: str = base_url
        self.timeout: float = timeout
        self._client: _OpenAIClientProtocol | None = None

        # DashScope thinking controls
        enable_thinking_env = os.getenv("DASHSCOPE_ENABLE_THINKING", "false").lower()
        self.enable_thinking = enable_thinking_env in ("true", "1")

        thinking_budget_env = os.getenv("DASHSCOPE_THINKING_BUDGET")
        self.thinking_budget = 256
        if thinking_budget_env:
            try:
                self.thinking_budget = int(thinking_budget_env)
            except ValueError:
                pass

        # 初始化日志：脱敏打印配置（不打印完整 Key）
        api_key_present = bool(self.api_key)
        api_key_prefix = ""
        if self.api_key:
            # sk- 开头的 Key 显示前9位，其他显示前6位
            prefix_len = 9 if self.api_key.startswith("sk-") else 6
            api_key_prefix = self.api_key[:prefix_len]

        logger.info(
            f"[LLM INIT]\n"
            f"provider=qwen\n"
            f"base_url={self.base_url}\n"
            f"model={self.model}\n"
            f"api_key_present={str(api_key_present).lower()}\n"
            f"api_key_prefix={api_key_prefix}\n"
            f"enable_thinking={str(self.enable_thinking).lower()}\n"
            f"thinking_budget={self.thinking_budget}"
        )

    def _get_client(self) -> _OpenAIClientProtocol:
        if not self.api_key:
            raise EnvironmentError(
                "缺少 API Key。请设置环境变量 DASHSCOPE_API_KEY_BAILIAN（百炼普通接口，优先）"
                + "或 DASHSCOPE_API_KEY（Coding Plan，回退）。"
            )

        if self._client is None:
            try:
                openai_module = importlib.import_module("openai")
            except ImportError as exc:
                raise ImportError("openai 未安装。请运行: pip install openai") from exc

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

        extra_body: dict[str, object] = {
            "enable_thinking": self.enable_thinking,
        }
        if self.enable_thinking:
            extra_body["thinking_budget"] = self.thinking_budget
        payload["extra_body"] = extra_body

        start_time = time.perf_counter()
        try:
            completion_obj = self._get_client().chat.completions.create(**payload)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"[LLM SUCCESS]\nmodel={self.model}\nlatency_ms={latency_ms}")
        except Exception as e:
            # 错误处理：提取关键信息并打印详细日志（用于调试 API 问题）
            status_code = getattr(e, "status_code", "N/A")
            response_text = "N/A"
            request_id = "N/A"

            # 尝试从异常对象提取 HTTP 响应信息
            if hasattr(e, "response"):
                resp = getattr(e, "response")
                if hasattr(resp, "text"):
                    response_text = resp.text
                elif hasattr(resp, "content"):
                    try:
                        response_text = resp.content.decode("utf-8", errors="replace")
                    except (UnicodeDecodeError, AttributeError, OSError):
                        response_text = str(resp.content)

                # 从响应头提取 request_id（用于向阿里云反馈问题）
                if hasattr(resp, "headers"):
                    request_id = (
                        resp.headers.get("x-request-id")
                        or resp.headers.get("request-id")
                        or "N/A"
                    )

            # 如果响应体是 JSON，尝试从 body 提取 request_id
            if request_id == "N/A" and response_text != "N/A":
                try:
                    body = json.loads(response_text)
                    if isinstance(body, dict):
                        request_id = (
                            body.get("request_id")
                            or body.get("requestId")
                            or (
                                body.get("error", {})
                                if isinstance(body.get("error"), dict)
                                else {}
                            ).get("request_id")
                            or "N/A"
                        )
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

            # 打印详细错误日志（包含 status_code、model、base_url、响应体、request_id）
            logger.error(
                f"[LLM ERROR]\n"
                + f"status_code={status_code}\n"
                + f"model={self.model}\n"
                + f"base_url={self.base_url}\n"
                + f"response_text={response_text}\n"
                + f"request_id={request_id}"
            )
            raise

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
            function_dict = self._as_dict(
                item_dict.get("function") or {}, "tool_call.function"
            )

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
    ) -> tuple[object | None, str]:
        try:
            return json.loads(content), content
        except json.JSONDecodeError:
            assistant_message: dict[str, object] = {
                "role": "assistant",
                "content": content,
            }
            repair_instruction: dict[str, object] = {
                "role": "user",
                "content": "The previous output is not valid JSON. Output ONLY a valid JSON object with no markdown, no code fences, no explanation. Fix all syntax errors: unclosed quotes, missing commas, unescaped characters.",
            }
            repair_messages = [
                *request_messages,
                assistant_message,
                repair_instruction,
            ]
            try:
                repair_completion = self._create_completion(
                    messages=repair_messages,
                    tools=None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )

                choices = self._as_list(
                    repair_completion.get("choices"), "completion.choices"
                )
                if not choices:
                    logger.warning(
                        "Model returned no choices while repairing JSON, returning None"
                    )
                    return None, content

                repair_choice = self._as_dict(choices[0], "completion.choices[0]")
                repair_message = self._as_dict(
                    repair_choice.get("message") or {}, "choice.message"
                )
                repaired_content = str(repair_message.get("content") or "")

                try:
                    return json.loads(repaired_content), repaired_content
                except json.JSONDecodeError as exc:
                    logger.warning(f"JSON parsing failed after repair attempt: {exc}")
                    return None, content
            except Exception as e:
                logger.warning(f"Repair attempt failed with exception: {e}")
                return None, content

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
        request_messages = self._prepare_messages(
            validated_messages, json_output=json_output
        )

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
