#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.semantic_search_tool import semantic_search
from src.tools.hybrid_recommend_tool import hybrid_recommend, _to_float
from src.recommender.music_recommender import MusicRecommender

EVAL_QUERIES = [
    {"query": "我想听适合学习的轻音乐", "category": "learning"},
    {"query": "适合专注工作的背景音乐", "category": "learning"},
    {"query": "安静的钢琴曲", "category": "learning"},
    {"query": "我现在有点emo，想听安静一点的歌", "category": "emo"},
    {"query": "心情不好，想听治愈的歌", "category": "emo"},
    {"query": "悲伤的夜晚想听歌", "category": "emo"},
    {"query": "来点适合夜跑的高能量音乐", "category": "running"},
    {"query": "健身时听的动感音乐", "category": "running"},
    {"query": "晨跑适合的歌", "category": "running"},
    {"query": "我想听摇滚乐", "category": "genre"},
    {"query": "推荐一些电子音乐", "category": "genre"},
    {"query": "想听爵士乐", "category": "genre"},
    {"query": "民谣风格的歌", "category": "genre"},
    {"query": "随便推荐点好听的歌", "category": "vague"},
    {"query": "最近很火的歌", "category": "vague"},
    {"query": "适合下雨天听的歌", "category": "vague"},
    {"query": "回忆过去的歌", "category": "vague"},
    {"query": "适合约会的浪漫歌曲", "category": "vague"},
    {"query": "开车时听的歌", "category": "vague"},
    {"query": "周末放松的音乐", "category": "vague"},
]

def evaluate_results(results: list) -> dict:
    if not results:
        return {"relevance": 1, "diversity": 1}
    
    artists = set()
    titles = set()
    relevance_scores = []
    
    for item in results:
        if not isinstance(item, dict):
            continue
        artist = str(item.get("artist", "") or "").lower()
        title = str(item.get("title", "") or "").lower()
        artists.add(artist)
        titles.add(title)
        sim = _to_float(item.get("similarity") or item.get("semantic_similarity") or 0)
        relevance_scores.append(sim)
    
    n = len(results)
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    
    if avg_relevance >= 0.25:
        relevance = 4
    elif avg_relevance >= 0.22:
        relevance = 3
    elif avg_relevance >= 0.20:
        relevance = 2
    else:
        relevance = 1
    
    unique_ratio = len(titles) / n if n > 0 else 0
    artist_ratio = len(artists) / n if n > 0 else 0
    
    if unique_ratio >= 0.9 and artist_ratio >= 0.7:
        diversity = 5
    elif unique_ratio >= 0.8 and artist_ratio >= 0.5:
        diversity = 4
    elif unique_ratio >= 0.6:
        diversity = 3
    elif unique_ratio >= 0.4:
        diversity = 2
    else:
        diversity = 1
    
    return {
        "relevance": relevance,
        "diversity": diversity,
        "notes": f"avg_sim={avg_relevance:.3f}, unique={len(titles)}/{n}"
    }

def run_evaluation():
    output_path = project_root / ".sisyphus" / "tmp" / "recommendation_quality_eval_v2.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    recommender = MusicRecommender()
    seed_id = next(iter(recommender.item_to_internal), None)
    seed_name = recommender.metadata.get(seed_id, "Adelitas Way - Dirty Little Thing") if seed_id else "Adelitas Way - Dirty Little Thing"
    
    results = {"seed_song": seed_name, "evaluations": []}
    
    print("Running evaluation v2 (with CF Gating)...")
    
    for eval_item in EVAL_QUERIES:
        query = eval_item["query"]
        category = eval_item["category"]
        
        print(f"\nQuery [{category}]: {query[:20]}...")
        
        sem_res = semantic_search({"query_text": query, "top_k": 10})
        sem_items = sem_res.get("data", []) if sem_res.get("ok") else []
        sem_eval = evaluate_results(sem_items)
        
        hyb_fixed_res = hybrid_recommend({
            "query_text": query,
            "seed_song_name": seed_name,
            "top_k": 10,
            "w_sem": 0.6,
            "w_cf": 0.4
        })
        hyb_fixed_items = hyb_fixed_res.get("data", []) if hyb_fixed_res.get("ok") else []
        hyb_fixed_eval = evaluate_results(hyb_fixed_items)
        
        hyb_gated_res = hybrid_recommend({
            "query_text": query,
            "seed_song_name": seed_name,
            "top_k": 10,
            "intent": "recommend"
        })
        hyb_gated_items = hyb_gated_res.get("data", []) if hyb_gated_res.get("ok") else []
        hyb_gated_eval = evaluate_results(hyb_gated_items)
        
        results["evaluations"].append({
            "query": query,
            "category": category,
            "semantic_only": {"count": len(sem_items), "eval": sem_eval},
            "hybrid_fixed": {"count": len(hyb_fixed_items), "eval": hyb_fixed_eval},
            "hybrid_gated": {"count": len(hyb_gated_items), "eval": hyb_gated_eval}
        })
        
        print(f"  Sem: rel={sem_eval['relevance']}, div={sem_eval['diversity']}")
        print(f"  Hybrid(fixed): rel={hyb_fixed_eval['relevance']}, div={hyb_fixed_eval['diversity']}")
        print(f"  Hybrid(gated): rel={hyb_gated_eval['relevance']}, div={hyb_gated_eval['diversity']}")
    
    sem_rel = sum(e["semantic_only"]["eval"]["relevance"] for e in results["evaluations"]) / len(results["evaluations"])
    sem_div = sum(e["semantic_only"]["eval"]["diversity"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_fixed_rel = sum(e["hybrid_fixed"]["eval"]["relevance"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_fixed_div = sum(e["hybrid_fixed"]["eval"]["diversity"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_gated_rel = sum(e["hybrid_gated"]["eval"]["relevance"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_gated_div = sum(e["hybrid_gated"]["eval"]["diversity"] for e in results["evaluations"]) / len(results["evaluations"])
    
    results["summary"] = {
        "semantic_only": {"relevance": round(sem_rel, 2), "diversity": round(sem_div, 2)},
        "hybrid_fixed": {"relevance": round(hyb_fixed_rel, 2), "diversity": round(hyb_fixed_div, 2)},
        "hybrid_gated": {"relevance": round(hyb_gated_rel, 2), "diversity": round(hyb_gated_div, 2)}
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Semantic-only:  rel={sem_rel:.2f}, div={sem_div:.2f}")
    print(f"Hybrid(fixed):  rel={hyb_fixed_rel:.2f}, div={hyb_fixed_div:.2f}")
    print(f"Hybrid(gated):  rel={hyb_gated_rel:.2f}, div={hyb_gated_div:.2f}")
    print(f"\nResults saved to {output_path}")
    
    return results

if __name__ == "__main__":
    run_evaluation()