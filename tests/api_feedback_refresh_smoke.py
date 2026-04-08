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


def test_feedback_and_refresh():
    client = TestClient(app)
    session_id = None

    # 1) POST /chat with message "推荐点适合学习的歌" -> capture first recommendation id and full id list A.
    payload = {"message": "推荐点适合学习的歌"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    session_id = data["session_id"]
    recs_a = data["recommendations"]
    assert len(recs_a) > 0
    ids_a = [r["id"] for r in recs_a]
    first_id = ids_a[0]
    print(f"Step 1: Got {len(ids_a)} recommendations. First ID: {first_id}")

    # 2) POST /chat with same session_id, message "不喜欢 id: <first_id>" -> assert 200.
    payload = {"session_id": session_id, "message": f"不喜欢 id: {first_id}"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    print(f"Step 2: Disliked {first_id}")

    # 3) POST /chat with same session_id, message "换一批" -> capture id list B.
    payload = {"session_id": session_id, "message": "换一批"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    recs_b = data["recommendations"]
    ids_b = [r["id"] for r in recs_b]
    print(f"Step 3: Refreshed. Got {len(ids_b)} recommendations.")

    # 4) Assert <first_id> NOT in B.
    assert first_id not in ids_b, (
        f"Disliked ID {first_id} should not be in new recommendations {ids_b}"
    )
    print(f"Step 4: Verified {first_id} is NOT in B")

    # 5) Assert B is not identical to A (allow partial overlap).
    # Since "换一批" merges ALL previous IDs into exclude_ids, B should have NO overlap with A.
    overlap = set(ids_a).intersection(set(ids_b))
    assert len(overlap) == 0, (
        f"Refresh should exclude all previous IDs. Overlap found: {overlap}"
    )
    print("Step 5: Verified B has no overlap with A")


def test_refine_chat_replaces_recommendations_without_refresh_keyword():
    client = TestClient(app)

    first_response = client.post("/chat", json={"message": "推荐点适合学习的歌"})
    assert first_response.status_code == 200
    first_data = first_response.json()
    session_id = first_data["session_id"]
    first_ids = [item["id"] for item in first_data["recommendations"]]
    assert first_ids
    assert first_data["recommendation_action"] == "replace"

    refine_response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "我想要更欢快一点，最好适合跑步"},
    )
    assert refine_response.status_code == 200
    refine_data = refine_response.json()

    refine_ids = [item["id"] for item in refine_data["recommendations"]]
    assert refine_ids
    assert refine_data["recommendation_action"] == "replace"
    assert refine_data["state"]["scene"] == "跑步"
    assert refine_data["state"]["preferred_energy"] == "high"
    assert refine_ids != first_ids, (
        "Refine chat should produce a new recommendation list"
    )


if __name__ == "__main__":
    try:
        test_feedback_and_refresh()
        test_refine_chat_replaces_recommendations_without_refresh_keyword()
        print("api_feedback_refresh_smoke passed")
    except Exception as e:
        print(f"api_feedback_refresh_smoke FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
