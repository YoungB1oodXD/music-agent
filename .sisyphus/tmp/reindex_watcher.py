#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import subprocess
import os
from datetime import datetime

try:
    import chromadb
except ImportError:
    chromadb = None

INDEX_PATH = "index/chroma_bge_m3"
COLLECTION_NAME = "music_bge_collection"
TARGET_COUNT = 106573
POLL_INTERVAL = 300
STATUS_FILE = ".sisyphus/tmp/reindex_live_status.json"
DONE_FILE = ".sisyphus/tmp/reindex_audits_done.json"

def get_count():
    if chromadb is None:
        return "Error: chromadb not installed"
    
    if not os.path.exists(INDEX_PATH):
        return "Error: index path does not exist"
        
    try:
        client = chromadb.PersistentClient(path=INDEX_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        return collection.count()
    except Exception as e:
        return f"Error: {str(e)}"

def run_audits():
    results = {}
    
    cmd1 = [
        "python", "scripts/vector_retrieval_audit.py",
        "--out", ".sisyphus/tmp/vector_retrieval_after_reindex.json"
    ]
    try:
        res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding='utf-8')
        results["vector_retrieval_audit"] = {
            "return_code": res1.returncode
        }
    except Exception as e:
        results["vector_retrieval_audit"] = {
            "return_code": -1,
            "error": str(e)
        }
    
    cmd2 = [
        "python", "scripts/semantic_search_audit.py",
        "--out", ".sisyphus/tmp/semantic_search_tool_after_reindex.json"
    ]
    try:
        res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding='utf-8')
        results["semantic_search_audit"] = {
            "return_code": res2.returncode
        }
    except Exception as e:
        results["semantic_search_audit"] = {
            "return_code": -1,
            "error": str(e)
        }
    
    return results

def main():
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    
    while True:
        count = get_count()
        timestamp = datetime.now().isoformat()
        
        status = {
            "timestamp": timestamp,
            "current_count": count,
            "target_count": TARGET_COUNT,
            "status": "waiting"
        }
        
        if isinstance(count, int) and count >= TARGET_COUNT:
            status["status"] = "running_audits"
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=4, ensure_ascii=False)
            
            audit_results = run_audits()
            
            done_data = {
                "timestamp": datetime.now().isoformat(),
                "final_count": count,
                "audit_results": {
                    "vector_retrieval_audit": audit_results["vector_retrieval_audit"]["return_code"],
                    "semantic_search_audit": audit_results["semantic_search_audit"]["return_code"]
                }
            }
            
            with open(DONE_FILE, "w", encoding="utf-8") as f:
                json.dump(done_data, f, indent=4, ensure_ascii=False)
            
            print("DONE")
            break
        
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=4, ensure_ascii=False)
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()

