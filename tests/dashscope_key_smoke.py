# -*- coding: utf-8 -*-
"""
测试 QwenClient API Key 优先级和错误处理

优先级验证：
1. 显式 api_key 参数
2. DASHSCOPE_API_KEY_BAILIAN（百炼普通接口）
3. DASHSCOPE_API_KEY（Coding Plan，回退）
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.llm.clients.qwen_openai_compat import QwenClient

def test_key_wiring():
    """测试 API Key 优先级：显式参数 > BAILIAN > API_KEY"""
    orig_bailian = os.environ.get("DASHSCOPE_API_KEY_BAILIAN")
    orig_coding = os.environ.get("DASHSCOPE_API_KEY")
    
    try:
        # 测试1：只有 Coding Plan Key 时使用回退
        os.environ["DASHSCOPE_API_KEY"] = "coding_key"
        if "DASHSCOPE_API_KEY_BAILIAN" in os.environ:
            del os.environ["DASHSCOPE_API_KEY_BAILIAN"]
        
        client = QwenClient()
        assert client.api_key == "coding_key", f"Expected coding_key, got {client.api_key}"
        print("OK: QwenClient reads DASHSCOPE_API_KEY as fallback")

        # 测试2：Bailian Key 优先于 Coding Plan Key
        os.environ["DASHSCOPE_API_KEY_BAILIAN"] = "bailian_key"
        client2 = QwenClient()
        assert client2.api_key == "bailian_key", f"Expected bailian_key, got {client2.api_key}"
        print("OK: DASHSCOPE_API_KEY_BAILIAN overrides DASHSCOPE_API_KEY")

        # 测试3：显式参数优先级最高
        client3 = QwenClient(api_key="explicit_key")
        assert client3.api_key == "explicit_key", f"Expected explicit_key, got {client3.api_key}"
        print("OK: Explicit api_key overrides both env vars")

        # 测试4：缺少 Key 时抛出 EnvironmentError
        if "DASHSCOPE_API_KEY" in os.environ:
            del os.environ["DASHSCOPE_API_KEY"]
        if "DASHSCOPE_API_KEY_BAILIAN" in os.environ:
            del os.environ["DASHSCOPE_API_KEY_BAILIAN"]
        
        client_no_key = QwenClient()
        assert client_no_key.api_key is None
        
        messages: list[dict[str, object]] = [{"role": "user", "content": "hi"}]
        try:
            _ = client_no_key.chat(messages=messages)
            assert False, "Should have raised EnvironmentError"
        except EnvironmentError as e:
            err_msg = str(e)
            # 验证错误信息包含两个环境变量名
            assert "DASHSCOPE_API_KEY_BAILIAN" in err_msg, "Error should mention Bailian key"
            assert "DASHSCOPE_API_KEY" in err_msg, "Error should mention Coding key"
            print("OK: Missing keys raise EnvironmentError naming both env vars")

    finally:
        # 恢复原始环境变量
        if orig_bailian is not None:
            os.environ["DASHSCOPE_API_KEY_BAILIAN"] = orig_bailian
        elif "DASHSCOPE_API_KEY_BAILIAN" in os.environ:
            del os.environ["DASHSCOPE_API_KEY_BAILIAN"]
            
        if orig_coding is not None:
            os.environ["DASHSCOPE_API_KEY"] = orig_coding
        elif "DASHSCOPE_API_KEY" in os.environ:
            del os.environ["DASHSCOPE_API_KEY"]

if __name__ == "__main__":
    try:
        test_key_wiring()
        print("\nAll DashScope key wiring smoke tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

