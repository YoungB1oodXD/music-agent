# -*- coding: utf-8 -*-
import os
import sys
import importlib.util
from pathlib import Path
from typing import cast

import fastapi
from fastapi.testclient import TestClient

# Neutralize proxy env vars to avoid interference with local TestClient calls
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["NO_PROXY"] = "127.0.0.1,localhost,testserver"

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

os.environ["MUSIC_AGENT_LLM_MODE"] = "mock"

# Load src/api/app.py dynamically to avoid LSP import errors
app_path = project_root / "src" / "api" / "app.py"
spec = importlib.util.spec_from_file_location("src.api.app", str(app_path))
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load module from {app_path}")
module = importlib.util.module_from_spec(spec)
sys.modules["src.api.app"] = module
spec.loader.exec_module(module)
app = cast(fastapi.FastAPI, module.app)

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["llm_mode"] == "mock"
    print("GET /health passed")

def test_chat_smoke():
    client = TestClient(app)
    payload = {
        "message": "推荐点适合学习的歌"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    
    assert "session_id" in data
    assert isinstance(data["session_id"], str)
    assert len(data["session_id"]) > 0
    
    assert "assistant_text" in data
    assert isinstance(data["assistant_text"], str)
    assert len(data["assistant_text"]) > 0
    
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0
    
    for rec in data["recommendations"]:
        assert "id" in rec
        assert isinstance(rec["id"], str)
        assert "name" in rec
        assert isinstance(rec["name"], str)
        # reason is optional (str | None)
        if "reason" in rec and rec["reason"] is not None:
            assert isinstance(rec["reason"], str)
        # citations is a list
        assert "citations" in rec
        assert isinstance(rec["citations"], list)
    
    assert "state" in data
    state = data["state"]
    expected_state_keys = ["mood", "scene", "genre", "preferred_energy", "preferred_vocals"]
    for key in expected_state_keys:
        assert key in state
        
    print("POST /chat passed")
    print(f"Assistant: {data['assistant_text'][:50]}...")
    print(f"Recommendations: {data['recommendations'][:3]}")

if __name__ == "__main__":
    try:
        test_health()
        test_chat_smoke()
        print("api_chat_smoke passed")
    except Exception as e:
        print(f"api_chat_smoke FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
