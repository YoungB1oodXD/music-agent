#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def run_audit(out_path: str):
    queries = [
        "我想听适合学习的轻音乐",
        "我现在有点emo，想听安静一点的歌",
        "来点适合夜跑的高能量音乐"
    ]
    
    results_data: Dict[str, Any] = {
        "queries": [],
        "error": None
    }
    
    try:
        from src.searcher.music_searcher import MusicSearcher
        searcher = MusicSearcher()
        
        for query in queries:
            logger.info(f"Running query: {query}")
            results = searcher.search(query, top_k=10, include_documents=True)
            
            query_results = []
            similarities = []
            
            for r in results:
                res = {
                    "title": r.get("title", "Unknown"),
                    "artist": r.get("artist", "Unknown"),
                    "genre": r.get("genre", ""),
                    "similarity": r.get("similarity", 0.0),
                    "distance": r.get("distance", 1.0),
                    "document": r.get("document", "")
                }
                query_results.append(res)
                similarities.append(res["similarity"])
            
            metrics = {}
            if similarities:
                metrics["top1"] = {"min": similarities[0], "max": similarities[0]}
                if len(similarities) >= 5:
                    metrics["top5"] = {"min": min(similarities[:5]), "max": max(similarities[:5])}
                else:
                    metrics["top5"] = {"min": min(similarities), "max": max(similarities)}
                
                if len(similarities) >= 10:
                    metrics["top10"] = {"min": min(similarities[:10]), "max": max(similarities[:10])}
                else:
                    metrics["top10"] = {"min": min(similarities), "max": max(similarities)}
            
            results_data["queries"].append({
                "query": query,
                "results": query_results,
                "metrics": metrics
            })
            
    except (FileNotFoundError, ImportError) as e:
        logger.error(f"Error initializing MusicSearcher: {e}")
        results_data["error"] = str(e)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        results_data["error"] = str(e)
    
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)
    
    print(out_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit vector retrieval quality.")
    parser.add_argument("--out", type=str, default=".sisyphus/tmp/vector_retrieval_baseline.json",
                        help="Output JSON path.")
    args = parser.parse_args()
    
    run_audit(args.out)
