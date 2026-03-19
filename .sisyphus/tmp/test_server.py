import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import sys
sys.path.insert(0, 'E:/Workspace/music_agent')

import time
import threading
import requests
import uvicorn

def run_server():
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, log_level="warning")

print("Starting server in background...")
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

print("Waiting for server to initialize...")
time.sleep(15)

print("\n=== Testing Health ===")
try:
    r = requests.get("http://localhost:8000/health", timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Testing Chat ===")
try:
    r = requests.post(
        "http://localhost:8000/chat",
        json={"message": "推荐一些适合学习的歌", "session_id": None},
        timeout=60,
    )
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Session ID: {data.get('session_id')}")
    print(f"Response: {data.get('assistant_text', '')[:300]}")
    recs = data.get("recommendations", [])
    print(f"Recommendations: {len(recs)}")
    if recs:
        for i, rec in enumerate(recs[:3]):
            print(f"  {i+1}. {rec.get('title')} - {rec.get('artist')}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Test Complete ===")