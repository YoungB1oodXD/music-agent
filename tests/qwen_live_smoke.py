# -*- coding: utf-8 -*-
"""
Qwen 大模型连通性测试

测试真实的 API 调用（需要配置有效的 API Key）：
- 使用 DASHSCOPE_API_KEY_BAILIAN（百炼普通接口，优先）
- 或 DASHSCOPE_API_KEY（Coding Plan，回退）

成功时会收到模型回复；失败时会打印详细的错误信息。
"""
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from src.llm.clients.qwen_openai_compat import QwenClient
except ImportError as e:
    print(f"[LLM ERROR] Failed to import QwenClient: {e}")
    sys.exit(1)

def main():
    """测试 Qwen API 真实连通性"""
    base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus")
    
    print("--- Qwen Live Smoke Test ---")
    
    try:
        client = QwenClient(model=model, base_url=base_url)
        api_key = client.api_key
        if not api_key:
            print("[LLM ERROR] No API key found. Please set DASHSCOPE_API_KEY_BAILIAN or DASHSCOPE_API_KEY.")
            sys.exit(1)
            
        # 脱敏打印 Key（不显示完整 Key）
        if api_key.startswith("sk-"):
            masked_key = f"{api_key[:9]}******{api_key[-4:]}" if len(api_key) > 13 else "sk-***"
        else:
            masked_key = f"{api_key[:6]}******{api_key[-4:]}" if len(api_key) > 10 else "***"
            
        print(f"Target: {base_url}")
        print(f"Model:  {model}")
        print(f"Key:    {masked_key}")
        print("Sending request...")

        # 发送测试请求
        messages: list[dict[str, object]] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你好，请只回复\"ok\""},
        ]

        response = client.chat(messages=messages, temperature=0.1)
        content = response.content
        
        print(f"\nAssistant response: {content}")
        
        if content and "ok" in content.lower():
            print("\nResult: SUCCESS")
        else:
            print("\nResult: FAILED (unexpected response)")

    except Exception as e:
        status_code = getattr(e, "status_code", "N/A")
        response_text = "N/A"
        request_id = "N/A"

        resp = getattr(e, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None)
            if isinstance(headers, dict):
                request_id = headers.get("x-request-id") or headers.get("request-id") or "N/A"
            else:
                get_header = getattr(headers, "get", None)
                if callable(get_header):
                    request_id = get_header("x-request-id") or get_header("request-id") or "N/A"

            text_attr = getattr(resp, "text", None)
            if isinstance(text_attr, str):
                response_text = text_attr
            else:
                content_attr = getattr(resp, "content", None)
                if isinstance(content_attr, (bytes, bytearray)):
                    response_text = bytes(content_attr).decode("utf-8", errors="replace")
                elif content_attr is not None:
                    response_text = str(content_attr)

        if request_id == "N/A" and response_text not in {"", "N/A"}:
            try:
                body = json.loads(response_text)
            except Exception:
                body = None
            if isinstance(body, dict):
                request_id = (
                    str(body.get("request_id") or "")
                    or str(body.get("requestId") or "")
                    or str(
                        (
                            body.get("error", {})
                            if isinstance(body.get("error"), dict)
                            else {}
                        ).get("request_id")
                        or ""
                    )
                    or request_id
                )

        print("\n[LLM ERROR]")
        print(f"status_code={status_code}")
        print(f"model={model}")
        print(f"base_url={base_url}")
        print(f"response_text={response_text}")
        print(f"request_id={request_id}")
        print(f"exception={type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
