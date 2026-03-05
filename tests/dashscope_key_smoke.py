import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.llm.clients.qwen_openai_compat import QwenClient

def test_key_wiring():
    original_env_key = os.environ.get("DASHSCOPE_API_KEY")
    
    try:
        os.environ["DASHSCOPE_API_KEY"] = "test_env_key"
        client = QwenClient()
        assert client.api_key == "test_env_key", f"Expected test_env_key, got {client.api_key}"
        print("OK: QwenClient reads DASHSCOPE_API_KEY from env")

        client_override = QwenClient(api_key="explicit_key")
        assert client_override.api_key == "explicit_key", f"Expected explicit_key, got {client_override.api_key}"
        print("OK: Explicit api_key overrides env")

        if "DASHSCOPE_API_KEY" in os.environ:
            del os.environ["DASHSCOPE_API_KEY"]
        
        client_no_key = QwenClient()
        assert client_no_key.api_key is None
        
        messages: list[dict[str, object]] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hi"},
        ]
        
        try:
            _ = client_no_key.chat(messages=messages)
            assert False, "Should have raised EnvironmentError for missing key"
        except EnvironmentError as e:
            assert "DASHSCOPE_API_KEY" in str(e), f"Error message should mention DASHSCOPE_API_KEY: {e}"
            print("OK: Missing key raises EnvironmentError mentioning DASHSCOPE_API_KEY")
        
    finally:
        if original_env_key is not None:
            os.environ["DASHSCOPE_API_KEY"] = original_env_key
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
