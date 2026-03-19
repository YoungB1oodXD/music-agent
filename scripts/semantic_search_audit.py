# -*- coding: utf-8 -*-
import json
import sys
import argparse
import os
import logging

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.ERROR, stream=sys.stderr, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Audit semantic search retrieval quality.")
    parser.add_argument("--out", default=".sisyphus/tmp/semantic_search_tool_after_query_expansion.json", help="Output JSON path")
    args = parser.parse_args()

    queries = [
        "我想听适合学习的轻音乐",
        "我现在有点emo，想听安静一点的歌",
        "来点适合夜跑的高能量音乐"
    ]

    output_data = {
        "queries": [],
        "error": None
    }

    try:
        # Import here to handle missing dependencies gracefully
        from src.tools.semantic_search_tool import semantic_search
        
        for query_text in queries:
            result = semantic_search({"query_text": query_text, "top_k": 10})
            
            if not result.get("ok"):
                query_entry = {
                    "query": query_text,
                    "error": result.get("error", "Unknown error"),
                    "results": [],
                    "metrics": None
                }
            else:
                data = result.get("data", [])
                similarities = [float(item["similarity"]) for item in data if "similarity" in item and item["similarity"] is not None]
                
                metrics = None
                if similarities:
                    top1 = similarities[0]
                    top5 = similarities[:5]
                    top10 = similarities[:10]
                    
                    metrics = {
                        "top1": {"min": top1, "max": top1},
                        "top5": {"min": min(top5), "max": max(top5)},
                        "top10": {"min": min(top10), "max": max(top10)}
                    }
                
                query_entry = {
                    "query": query_text,
                    "count": len(data),
                    "results": data,
                    "metrics": metrics
                }
            
            output_data["queries"].append(query_entry)

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        output_data["error"] = str(e)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(args.out)

if __name__ == "__main__":
    main()
