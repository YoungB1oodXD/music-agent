#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path

os.environ['MUSIC_AGENT_LLM_MODE'] = 'qwen'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

TEST_CASES = [
    {
        "name": "普通推荐",
        "messages": ["推荐一些适合学习的轻音乐"],
        "verify": lambda r: r.status_code == 200 and len(r.json().get("recommendations", [])) > 0
    },
    {
        "name": "多轮偏好细化",
        "messages": ["推荐一些适合学习的轻音乐", "不要太吵", "最好是纯音乐"],
        "verify": lambda r: r.status_code == 200 and r.json().get("state", {}).get("preferred_vocals") == "instrumental"
    },
    {
        "name": "like后推荐收敛",
        "messages": ["推荐一些适合学习的轻音乐"],
        "feedback": {"type": "like", "track_index": 0},
        "verify": lambda r: r.status_code == 200
    },
    {
        "name": "dislike后方向调整",
        "messages": ["推荐一些摇滚乐"],
        "feedback": {"type": "dislike", "track_index": 0},
        "verify": lambda r: r.status_code == 200
    },
    {
        "name": "refresh后结果变化",
        "messages": ["推荐一些电子音乐", "换一批"],
        "verify": lambda r: r.status_code == 200
    }
]

def run_e2e_tests():
    output_path = project_root / ".sisyphus" / "evidence" / "e2e_test_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = []
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("E2E TEST SUITE")
    print("=" * 60)
    
    for test_case in TEST_CASES:
        test_name = test_case["name"]
        messages = test_case["messages"]
        verify_fn = test_case["verify"]
        
        print(f"\nTest: {test_name}")
        
        session_id = None
        test_result = {
            "name": test_name,
            "steps": [],
            "passed": False,
            "debug_info": []
        }
        
        for i, msg in enumerate(messages):
            payload = {"message": msg}
            if session_id:
                payload["session_id"] = session_id
            
            start_time = time.perf_counter()
            r = client.post("/chat", json=payload)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            body = r.json()
            session_id = body.get("session_id")
            debug = body.get("debug", {})
            
            step = {
                "message": msg,
                "status_code": r.status_code,
                "latency_ms": latency_ms,
                "llm_called": debug.get("llm_called", False),
                "recommendations_count": len(body.get("recommendations", [])),
                "assistant_text": body.get("assistant_text", "")[:100] + "..."
            }
            test_result["steps"].append(step)
            test_result["debug_info"].append(debug)
            
            print(f"  Step {i+1}: {msg[:30]}...")
            print(f"    Status: {r.status_code}, LLM Called: {debug.get('llm_called')}, Latency: {latency_ms}ms")
            
            if "feedback" in test_case and i == len(messages) - 1:
                fb = test_case["feedback"]
                recs = body.get("recommendations", [])
                if recs and fb["track_index"] < len(recs):
                    track_id = recs[fb["track_index"]].get("id")
                    fb_response = client.post("/feedback", json={
                        "session_id": session_id,
                        "feedback_type": fb["type"],
                        "track_id": track_id,
                        "track_metadata": {},
                        "recommendation_context": {}
                    })
                    print(f"    Feedback: {fb['type']} -> Status: {fb_response.status_code}")
                    test_result["steps"].append({
                        "feedback": fb["type"],
                        "status_code": fb_response.status_code
                    })
        
        try:
            test_passed = verify_fn(r)
        except Exception as e:
            test_passed = False
            test_result["error"] = str(e)
        
        test_result["passed"] = test_passed
        results.append(test_result)
        
        if test_passed:
            passed += 1
            print(f"  Result: PASSED")
        else:
            failed += 1
            print(f"  Result: FAILED")
    
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)
    
    summary = {
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "test_results": results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to {output_path}")
    return failed == 0

if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)