import subprocess
import sys
import time
import requests

proc = subprocess.Popen(
    [sys.executable, "scripts/run_api.py"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

print("Server starting...")
time.sleep(10)

try:
    r = requests.get("http://localhost:8000/health", timeout=10)
    print(f"Health: {r.status_code}")
    print(r.json())
except Exception as e:
    print(f"Health error: {e}")

try:
    r = requests.post(
        "http://localhost:8000/chat",
        json={"message": "推荐一些适合学习的歌", "session_id": None},
        timeout=30,
    )
    print(f"Chat: {r.status_code}")
    data = r.json()
    print(f"Session: {data.get('session_id')}")
    print(f"Response: {data.get('assistant_text', '')[:200]}")
    print(f"Recommendations: {len(data.get('recommendations', []))}")
    if data.get("recommendations"):
        rec = data["recommendations"][0]
        print(f"First: {rec.get('title')} by {rec.get('artist')}")
except Exception as e:
    print(f"Chat error: {e}")

proc.terminate()
print("Done")