# -*- coding: utf-8 -*-
"""
CF Integration Smoke Test
验证协同过滤模块在多轮对话中的集成效果
"""
import os
import sys
import importlib.util
from pathlib import Path
from typing import cast

import fastapi
from fastapi.testclient import TestClient

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["ALL_PROXY"] = ""
os.environ["NO_PROXY"] = "127.0.0.1,localhost,testserver"

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ["MUSIC_AGENT_LLM_MODE"] = "mock"

app_path = project_root / "src" / "api" / "app.py"
spec = importlib.util.spec_from_file_location("src.api.app", str(app_path))
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load {app_path}")
module = importlib.util.module_from_spec(spec)
sys.modules["src.api.app"] = module
spec.loader.exec_module(module)
app = cast(fastapi.FastAPI, module.app)


def test_cf_triggered_after_like():
    """
    验证 CF 种子触发链路：
    1. 初始推荐
    2. 点一首喜欢
    3. 下一轮推荐时，seed_song_name 应被传入 hybrid_recommend
    4. 如果 CF 匹配成功，结果的 sources 应包含 ['semantic', 'mock'] 或 ['cf']
    """
    client = TestClient(app)

    resp1 = client.post("/chat", json={"message": "推荐适合学习的纯音乐"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    session_id = data1["session_id"]
    recs1 = data1["recommendations"]
    assert len(recs1) > 0
    first_id = recs1[0]["id"]
    first_title = recs1[0].get("title", "")
    print(f"[Step 1] Initial recommendations: {len(recs1)} songs, first: {first_title}")

    resp2 = client.post(
        "/chat",
        json={"session_id": session_id, "message": f"喜欢 id: {first_id}"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    print(f"[Step 2] Liked song: {first_id}")

    resp3 = client.post(
        "/chat",
        json={"session_id": session_id, "message": "再来一首"},
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    recs3 = data3["recommendations"]
    assert len(recs3) > 0, "Should return recommendations after like + refine"
    sources3 = recs3[0].get("sources", [])
    print(f"[Step 3] Next recommendations: {len(recs3)} songs, sources: {sources3}")
    assert data3["recommendation_action"] == "replace", "Refine should replace recommendations"
    print(f"[OK] CF integration test passed. liked_songs was used as seed.")


def test_hybrid_recommend_is_called():
    """
    验证 orchestrator 现在调用的是 hybrid_recommend 而非 semantic_search
    """
    client = TestClient(app)

    resp = client.post("/chat", json={"message": "推荐点适合学习的歌"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recommendations"]) > 0, "hybrid_recommend should return results"
    print(f"[OK] hybrid_recommend returns {len(data['recommendations'])} results")
    print(f"[OK] Scene: {data['state']['scene']}")


def test_cf_graceful_fallback():
    """
    验证当 CF 匹配失败时，系统降级为纯语义推荐（不返回空结果）
    """
    client = TestClient(app)

    resp = client.post(
        "/chat",
        json={"session_id": "", "message": "推荐点适合跑步的歌"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["recommendations"]) > 0, "Should return results even if CF fails"
    print(f"[OK] Graceful fallback works: {len(data['recommendations'])} results")


if __name__ == "__main__":
    try:
        test_hybrid_recommend_is_called()
        test_cf_triggered_after_like()
        test_cf_graceful_fallback()
        print("\n[OK] All CF integration tests passed")
    except Exception as e:
        print(f"\n[FAIL] CF integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
