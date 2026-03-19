#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen Real-Mode Smoke Suite
Verifies the real pipeline (Qwen + Chroma + CF/Hybrid + /chat) without modifying core code.
"""

import os
import sys
import time
import logging
import json
from pathlib import Path
from typing import Any, Dict, List

os.environ["MUSIC_AGENT_LLM_MODE"] = "qwen"
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class RedactingStreamHandler(logging.StreamHandler[Any]):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if "sk-" in msg:
                msg = msg.replace("sk-", "sk-REDACTED")
            if "api_key_prefix=" in msg:
                import re
                msg = re.sub(r"api_key_prefix=[^\s\n]+", "api_key_prefix=REDACTED", msg)
            
            try:
                if self.stream:
                    self.stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                encoding = getattr(self.stream, 'encoding', 'utf-8') or 'utf-8'
                safe_msg = msg.encode(encoding, errors='replace').decode(encoding)
                if self.stream:
                    self.stream.write(safe_msg + self.terminator)
            
            self.flush()
        except Exception:
            self.handleError(record)

class LogCaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.logs: List[str] = []
    def emit(self, record: logging.LogRecord) -> None:
        self.logs.append(self.format(record))

log_capture = LogCaptureHandler()
logging.getLogger().addHandler(log_capture)
for h in logging.getLogger().handlers[:]:
    if isinstance(h, logging.StreamHandler) and not isinstance(h, (RedactingStreamHandler, LogCaptureHandler)):
        logging.getLogger().removeHandler(h)

logging.getLogger().addHandler(RedactingStreamHandler(sys.stdout))
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger("qwen_smoke")

try:
    from fastapi.testclient import TestClient
    from src.api.app import app
    from src.llm.clients import QwenClient
    from src.searcher.music_searcher import MusicSearcher
    from src.recommender.music_recommender import MusicRecommender
    from src.tools.semantic_search_tool import semantic_search
    from src.tools.hybrid_recommend_tool import hybrid_recommend
except ImportError as e:
    print(f"CRITICAL: Missing dependencies: {e}")
    sys.exit(1)

def redact_text(text: str) -> str:
    import re
    text = text.replace("sk-", "sk-REDACTED")
    text = re.sub(r"api_key_prefix=[^\s\n]+", "api_key_prefix=REDACTED", text)
    return text

def main():
    evidence_path = project_root / ".sisyphus" / "evidence" / "qwen_smoke_suite.md"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = {
        "health_check": "PENDING",
        "llm_direct_call": "PENDING",
        "chroma_count": "PENDING",
        "semantic_search": "PENDING",
        "hybrid_recommend": "PENDING",
        "chat_endpoint": "PENDING"
    }
    errors: List[str] = []
    
    count: int = 0
    sem_res: Dict[str, Any] = {}
    hyb_res: Dict[str, Any] = {}
    body: Dict[str, Any] = {}
    
    start_time = time.time()
    
    try:
        logger.info("Step 1: Verifying /health...")
        client = TestClient(app)
        resp = client.get("/health")
        if resp.status_code == 200 and resp.json().get("llm_mode") == "qwen":
            results["health_check"] = "PASS"
        else:
            results["health_check"] = "FAIL"
            errors.append(f"/health failed: {resp.text}")

        logger.info("Step 2: Verifying QwenClient direct call...")
        qwen = QwenClient()
        chat_resp = qwen.chat([{"role": "user", "content": "Hello, are you Qwen?"}])
        if chat_resp.content and any("[LLM SUCCESS]" in log for log in log_capture.logs):
            results["llm_direct_call"] = "PASS"
        else:
            results["llm_direct_call"] = "FAIL"
            errors.append("QwenClient direct call failed or [LLM SUCCESS] not found in logs")

        logger.info("Step 3: Verifying Chroma collection...")
        searcher = MusicSearcher()
        if searcher.collection is not None:
            count = searcher.collection.count()
            if count > 0:
                results["chroma_count"] = f"PASS ({count} docs)"
            else:
                results["chroma_count"] = "FAIL (0 docs)"
                errors.append("Chroma collection is empty")
        else:
            results["chroma_count"] = "FAIL (no collection)"
            errors.append("Chroma collection is None")

        logger.info("Step 4: Verifying semantic_search tool...")
        sem_res = semantic_search({"query_text": "适合学习的轻音乐", "top_k": 3})
        if sem_res.get("ok") and isinstance(sem_res.get("data"), list) and len(sem_res["data"]) > 0:
            first = sem_res["data"][0]
            required = ["title", "artist", "genre", "track_id"]
            if all(k in first for k in required):
                results["semantic_search"] = "PASS"
            else:
                results["semantic_search"] = "FAIL (missing fields)"
                errors.append(f"semantic_search missing fields: {list(first.keys())}")
        else:
            results["semantic_search"] = "FAIL"
            errors.append(f"semantic_search failed: {sem_res.get('error')}")

        logger.info("Step 5: Verifying hybrid_recommend tool...")
        recommender = MusicRecommender()
        if not recommender.item_to_internal:
            results["hybrid_recommend"] = "FAIL (no CF items)"
            errors.append("MusicRecommender has no items in item_to_internal")
        else:
            seed_id = next(iter(recommender.item_to_internal))
            seed_name = recommender.metadata.get(seed_id, seed_id)
            logger.info(f"Using seed: {seed_name} ({seed_id})")
            
            hyb_res = hybrid_recommend({
                "query_text": "适合学习的轻音乐",
                "top_k": 8,
                "seed_song_name": seed_name,
                "w_sem": 0.6,
                "w_cf": 0.4
            })
            
            if hyb_res.get("ok") and isinstance(hyb_res.get("data"), list) and len(hyb_res["data"]) > 0:
                data = hyb_res["data"]
                has_cf = any("cf" in item.get("sources", []) or (item.get("cf_score") is not None and item.get("cf_score") > 0) for item in data)
                if has_cf:
                    results["hybrid_recommend"] = "PASS"
                else:
                    results["hybrid_recommend"] = "FAIL (no CF involvement)"
                    errors.append("hybrid_recommend returned results but none from CF")
            else:
                results["hybrid_recommend"] = "FAIL"
                errors.append(f"hybrid_recommend failed: {hyb_res.get('error')}")

        logger.info("Step 6: Verifying /chat endpoint...")
        chat_payload = {"message": "我想听适合学习的轻音乐"}
        chat_resp = client.post("/chat", json=chat_payload)
        if chat_resp.status_code == 200:
            body = chat_resp.json()
            recs = body.get("recommendations", [])
            if body.get("assistant_text") and len(recs) > 0:
                if all(not str(r.get("id", "")).startswith("mock_") for r in recs):
                    results["chat_endpoint"] = "PASS"
                else:
                    results["chat_endpoint"] = "FAIL (mock IDs found)"
                    errors.append(f"Mock IDs found in recommendations: {[r.get('id') for r in recs]}")
            else:
                results["chat_endpoint"] = "FAIL (empty response)"
                errors.append("Chat response missing assistant_text or recommendations")
        else:
            results["chat_endpoint"] = "FAIL"
            errors.append(f"/chat failed with status {chat_resp.status_code}: {chat_resp.text}")

    except Exception as e:
        logger.error(f"Unexpected error during smoke test: {e}", exc_info=True)
        errors.append(f"Unexpected error: {e}")

    elapsed = time.time() - start_time
    success = all("PASS" in str(v) for k, v in results.items())
    
    report = [
        "# Qwen Real-Mode Smoke Suite Report",
        f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Duration: {elapsed:.2f}s",
        f"Status: {'✅ SUCCESS' if success else '❌ FAILURE'}",
        "",
        "## Results",
        f"- **Health Check**: {results['health_check']}",
        f"- **LLM Direct Call**: {results['llm_direct_call']}",
        f"- **Chroma Count**: {results['chroma_count']}",
        f"- **Semantic Search**: {results['semantic_search']}",
        f"- **Hybrid Recommend**: {results['hybrid_recommend']}",
        f"- **Chat Endpoint**: {results['chat_endpoint']}",
        ""
    ]
    
    if errors:
        report.append("## Errors")
        for err in errors:
            report.append(f"- {err}")
        report.append("")
    
    report.append("## Evidence Details")
    report.append("### LLM Call Status")
    llm_logs = [log for log in log_capture.logs if "[LLM" in log]
    if llm_logs:
        report.append("```")
        for log in llm_logs:
            report.append(redact_text(log))
        report.append("```")
    else:
        report.append("No LLM logs captured.")
    
    report.append("### Chroma Collection Count")
    report.append(f"Count: {count}")
    
    report.append("### Semantic Search Sample")
    if sem_res.get("ok") and sem_res.get("data"):
        report.append("```json")
        report.append(json.dumps(sem_res["data"][0], indent=2, ensure_ascii=False))
        report.append("```")
    
    report.append("### Hybrid Recommend Sample")
    if hyb_res.get("ok") and hyb_res.get("data"):
        # Prefer a CF-involved sample if available
        sample = hyb_res["data"][0]
        for item in hyb_res["data"]:
            if "cf" in item.get("sources", []) or (item.get("cf_score") is not None and item.get("cf_score") > 0):
                sample = item
                break
        report.append("```json")
        report.append(json.dumps(sample, indent=2, ensure_ascii=False))
        report.append("```")
        
    report.append("### /chat Sample Summary")
    if body:
        report.append(f"Assistant Text Length: {len(body.get('assistant_text', ''))}")
        report.append(f"Recommendations Count: {len(body.get('recommendations', []))}")
        if body.get('recommendations'):
            report.append("First Rec ID: " + str(body['recommendations'][0].get('id')))
    
    report.append("\n## Final Conclusion")
    if success:
        report.append("REAL PIPELINE VERIFIED")
    else:
        report.append("PIPELINE VERIFICATION FAILED")

    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    if success:
        print("\nREAL PIPELINE VERIFIED")
        sys.exit(0)
    else:
        print("\nPIPELINE VERIFICATION FAILED")
        for err in errors:
            print(f"ERROR: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
