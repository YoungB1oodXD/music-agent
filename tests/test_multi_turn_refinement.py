# -*- coding: utf-8 -*-
"""
多轮对话推荐系统 smoke test
验证：学习 → 跑步 → 不要人声 → 换一批 的完整流程
"""

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


def test_multi_turn_refinement_flow():
    """
    完整多轮对话流程验证：
    1. 初次推荐（学习场景）
    2. 修正为跑步场景（高能量）
    3. 修正为纯音乐（无人声）
    4. 换一批（当前偏好下翻页）
    5. 解释型对话（保留列表）
    """
    client = TestClient(app)
    session_id = None

    # Step 1: 初次推荐 - 学习场景
    print("\n=== Step 1: 初次推荐 - 学习场景 ===")
    response = client.post("/chat", json={"message": "推荐点适合学习的歌"})
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    first_recs = data["recommendations"]
    first_ids = [r["id"] for r in first_recs]

    assert len(first_recs) > 0, "应该返回推荐结果"
    assert data["recommendation_action"] == "replace", "初次推荐应该替换列表"
    assert data["state"]["scene"] == "学习", "应该识别为学习场景"
    print(f"OK: 获得 {len(first_recs)} 首推荐，场景: {data['state']['scene']}")

    # Step 2: 修正为跑步场景（高能量）
    print("\n=== Step 2: 修正为跑步场景（高能量） ===")
    response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "我想要更欢快一点，最好适合跑步"},
    )
    assert response.status_code == 200
    data = response.json()
    second_recs = data["recommendations"]
    second_ids = [r["id"] for r in second_recs]

    assert data["recommendation_action"] == "replace", "偏好修正应该替换列表"
    assert data["state"]["scene"] == "跑步", "应该更新为跑步场景"
    assert data["state"]["preferred_energy"] == "high", "应该识别为高能量"
    assert second_ids != first_ids, "推荐列表应该变化"
    print(
        f"[OK] 场景更新为: {data['state']['scene']}, 能量: {data['state']['preferred_energy']}"
    )
    print(
        f"[OK] 推荐列表已更新，与上一轮无重叠: {len(set(first_ids) & set(second_ids)) == 0}"
    )

    # Step 3: 修正为纯音乐（无人声）
    print("\n=== Step 3: 修正为纯音乐（无人声） ===")
    response = client.post(
        "/chat", json={"session_id": session_id, "message": "不要人声，来点纯音乐"}
    )
    assert response.status_code == 200
    data = response.json()
    third_recs = data["recommendations"]
    third_ids = [r["id"] for r in third_recs]

    assert data["recommendation_action"] == "replace", "偏好修正应该替换列表"
    assert data["state"]["preferred_vocals"] == "instrumental", "应该识别为纯音乐偏好"
    # 场景应该保持跑步（不是重置）
    assert data["state"]["scene"] == "跑步", "场景应该保持跑步"
    print(
        f"[OK] 声乐偏好: {data['state']['preferred_vocals']}, 场景保持: {data['state']['scene']}"
    )

    # Step 4: 换一批（当前偏好下翻页）
    print("\n=== Step 4: 换一批（当前偏好下翻页） ===")
    response = client.post(
        "/chat", json={"session_id": session_id, "message": "换一批"}
    )
    assert response.status_code == 200
    data = response.json()
    fourth_recs = data["recommendations"]
    fourth_ids = [r["id"] for r in fourth_recs]

    assert data["recommendation_action"] == "replace", "换一批应该替换列表"
    # 偏好应该保持不变
    assert data["state"]["scene"] == "跑步", "换一批应该保持跑步场景"
    assert data["state"]["preferred_energy"] == "high", "换一批应该保持高能量"
    assert data["state"]["preferred_vocals"] == "instrumental", "换一批应该保持纯音乐"
    # 应该排除上一批
    overlap = set(third_ids) & set(fourth_ids)
    assert len(overlap) == 0, f"换一批应该排除上一批，但发现重叠: {overlap}"
    print(
        f"[OK] 场景: {data['state']['scene']}, 能量: {data['state']['preferred_energy']}, 声乐: {data['state']['preferred_vocals']}"
    )
    print(f"[OK] 换一批成功，与上一轮无重叠")

    # Step 5: 解释型对话（不应该替换推荐列表）
    print("\n=== Step 5: 解释型对话（保留当前列表） ===")
    response = client.post(
        "/chat", json={"session_id": session_id, "message": "为什么推荐这些歌？"}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["recommendation_action"] == "preserve", "解释型对话应该保留列表"
    # 推荐列表应该为空（因为 explain 不触发工具调用）
    assert len(data["recommendations"]) == 0, "解释型对话不应该返回新推荐"
    print(f"[OK] 解释型对话保留列表，不返回新推荐")

    print("\n" + "=" * 50)
    print("[OK] 多轮对话流程验证通过！")
    print("=" * 50)
    print(f"\n完整流程:")
    print(f"  1. 学习场景 → {len(first_recs)} 首推荐")
    print(f"  2. 跑步+高能量 → {len(second_recs)} 首新推荐")
    print(f"  3. +纯音乐 → {len(third_recs)} 首新推荐")
    print(f"  4. 换一批 → {len(fourth_recs)} 首新推荐（同偏好翻页）")
    print(f"  5. 问原因 → 保留列表，仅文本回复")


if __name__ == "__main__":
    try:
        test_multi_turn_refinement_flow()
        print("\ntest_multi_turn_refinement_flow passed")
    except Exception as e:
        print(f"\ntest_multi_turn_refinement_flow FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
