#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path
from typing import Any

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.semantic_search_tool import semantic_search
from src.tools.hybrid_recommend_tool import hybrid_recommend, _to_float
from src.recommender.music_recommender import MusicRecommender

EVAL_QUERIES = [
    {"query": "我想听适合学习的轻音乐", "category": "learning", "expected_keywords": ["learning", "calm", "focus", "study"]},
    {"query": "适合专注工作的背景音乐", "category": "learning", "expected_keywords": ["focus", "work", "ambient"]},
    {"query": "安静的钢琴曲", "category": "learning", "expected_keywords": ["piano", "quiet", "calm"]},
    {"query": "我现在有点emo，想听安静一点的歌", "category": "emo", "expected_keywords": ["emo", "calm", "sad", "quiet"]},
    {"query": "心情不好，想听治愈的歌", "category": "emo", "expected_keywords": ["healing", "calm", "comfort"]},
    {"query": "悲伤的夜晚想听歌", "category": "emo", "expected_keywords": ["sad", "night", "slow"]},
    {"query": "来点适合夜跑的高能量音乐", "category": "running", "expected_keywords": ["run", "energy", "night", "fast"]},
    {"query": "健身时听的动感音乐", "category": "running", "expected_keywords": ["energy", "workout", "upbeat"]},
    {"query": "晨跑适合的歌", "category": "running", "expected_keywords": ["morning", "run", "energy"]},
    {"query": "我想听摇滚乐", "category": "genre", "expected_keywords": ["rock"]},
    {"query": "推荐一些电子音乐", "category": "genre", "expected_keywords": ["electronic", "electro"]},
    {"query": "想听爵士乐", "category": "genre", "expected_keywords": ["jazz"]},
    {"query": "民谣风格的歌", "category": "genre", "expected_keywords": ["folk"]},
    {"query": "随便推荐点好听的歌", "category": "vague", "expected_keywords": []},
    {"query": "最近很火的歌", "category": "vague", "expected_keywords": []},
    {"query": "适合下雨天听的歌", "category": "vague", "expected_keywords": ["rain", "slow", "calm"]},
    {"query": "回忆过去的歌", "category": "vague", "expected_keywords": ["memory", "nostalgia", "old"]},
    {"query": "适合约会的浪漫歌曲", "category": "vague", "expected_keywords": ["romantic", "love", "date"]},
    {"query": "开车时听的歌", "category": "vague", "expected_keywords": ["drive", "road", "travel"]},
    {"query": "周末放松的音乐", "category": "vague", "expected_keywords": ["relax", "weekend", "chill"]},
]

RUBRIC = {
    "relevance": {
        5: "Highly relevant - all results match query intent",
        4: "Mostly relevant - most results match, minor mismatches",
        3: "Moderately relevant - half match, half don't",
        2: "Mostly irrelevant - few results match",
        1: "Completely irrelevant"
    },
    "diversity": {
        5: "High diversity - different artists, genres, styles",
        4: "Good diversity - some repetition but varied",
        3: "Moderate diversity - noticeable patterns",
        2: "Low diversity - many duplicates or similar items",
        1: "No diversity - all same or near-duplicates"
    },
    "explanation": {
        5: "Clear reasons that directly explain relevance",
        4: "Good reasons with minor gaps",
        3: "Generic reasons that could apply to anything",
        2: "Weak or misleading reasons",
        1: "No meaningful reasons"
    }
}

def evaluate_results(results: list[dict], expected_keywords: list[str]) -> dict:
    if not results:
        return {"relevance": 1, "diversity": 1, "explanation": 1, "notes": "No results returned"}
    
    artists = set()
    titles = set()
    genres = set()
    keyword_matches = 0
    relevance_scores = []
    
    for item in results:
        if not isinstance(item, dict):
            continue
        artist = str(item.get("artist", "") or "").lower()
        title = str(item.get("title", "") or "").lower()
        genre = str(item.get("genre", "") or "").lower()
        
        artists.add(artist)
        titles.add(title)
        if genre:
            genres.add(genre)
        
        combined = f"{artist} {title} {genre}"
        for kw in expected_keywords:
            if kw.lower() in combined:
                keyword_matches += 1
                break
        
        sim = _to_float(item.get("similarity") or item.get("semantic_similarity") or 0)
        relevance_scores.append(sim)
    
    n = len(results)
    keyword_ratio = keyword_matches / n if n > 0 else 0
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    
    if keyword_ratio >= 0.8 and avg_relevance >= 0.25:
        relevance = 5
    elif keyword_ratio >= 0.6 and avg_relevance >= 0.22:
        relevance = 4
    elif keyword_ratio >= 0.4 and avg_relevance >= 0.20:
        relevance = 3
    elif keyword_ratio >= 0.2:
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
    
    explanation = 3
    
    return {
        "relevance": relevance,
        "diversity": diversity,
        "explanation": explanation,
        "notes": f"keyword_match={keyword_matches}/{n}, avg_sim={avg_relevance:.3f}, unique_titles={len(titles)}/{n}, unique_artists={len(artists)}"
    }

def run_evaluation():
    output_path = project_root / ".sisyphus" / "tmp" / "recommendation_quality_eval.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    recommender = MusicRecommender()
    seed_id = next(iter(recommender.item_to_internal), None)
    seed_name = recommender.metadata.get(seed_id, "Adelitas Way - Dirty Little Thing") if seed_id else "Adelitas Way - Dirty Little Thing"
    
    results = {
        "seed_song": seed_name,
        "rubric": RUBRIC,
        "evaluations": []
    }
    
    print("Running recommendation quality evaluation...")
    print(f"Seed song for hybrid: {seed_name}")
    
    for eval_item in EVAL_QUERIES:
        query = eval_item["query"]
        category = eval_item["category"]
        expected_keywords = eval_item["expected_keywords"]
        
        print(f"\nQuery [{category}]: {query}")
        
        sem_res = semantic_search({"query_text": query, "top_k": 10})
        sem_items = sem_res.get("data", []) if sem_res.get("ok") else []
        
        hyb_res = hybrid_recommend({
            "query_text": query,
            "seed_song_name": seed_name,
            "top_k": 10,
            "w_sem": 0.6,
            "w_cf": 0.4
        })
        hyb_items = hyb_res.get("data", []) if hyb_res.get("ok") else []
        
        sem_eval = evaluate_results(sem_items, expected_keywords)
        hyb_eval = evaluate_results(hyb_items, expected_keywords)
        
        sem_titles = [i.get("title", "") for i in sem_items if isinstance(i, dict)][:5]
        hyb_titles = [i.get("title", "") for i in hyb_items if isinstance(i, dict)][:5]
        
        eval_result = {
            "query": query,
            "category": category,
            "expected_keywords": expected_keywords,
            "semantic_only": {
                "count": len(sem_items),
                "evaluation": sem_eval,
                "top_titles": sem_titles
            },
            "hybrid": {
                "count": len(hyb_items),
                "evaluation": hyb_eval,
                "top_titles": hyb_titles
            },
            "improvement": {
                "relevance": hyb_eval["relevance"] - sem_eval["relevance"],
                "diversity": hyb_eval["diversity"] - sem_eval["diversity"],
                "explanation": hyb_eval["explanation"] - sem_eval["explanation"]
            }
        }
        
        results["evaluations"].append(eval_result)
        
        print(f"  Semantic: rel={sem_eval['relevance']}, div={sem_eval['diversity']}, count={len(sem_items)}")
        print(f"  Hybrid:   rel={hyb_eval['relevance']}, div={hyb_eval['diversity']}, count={len(hyb_items)}")
        print(f"  Improvement: rel={eval_result['improvement']['relevance']:+d}, div={eval_result['improvement']['diversity']:+d}")
    
    sem_rel_avg = sum(e["semantic_only"]["evaluation"]["relevance"] for e in results["evaluations"]) / len(results["evaluations"])
    sem_div_avg = sum(e["semantic_only"]["evaluation"]["diversity"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_rel_avg = sum(e["hybrid"]["evaluation"]["relevance"] for e in results["evaluations"]) / len(results["evaluations"])
    hyb_div_avg = sum(e["hybrid"]["evaluation"]["diversity"] for e in results["evaluations"]) / len(results["evaluations"])
    
    results["summary"] = {
        "total_queries": len(EVAL_QUERIES),
        "semantic_only_avg": {"relevance": round(sem_rel_avg, 2), "diversity": round(sem_div_avg, 2)},
        "hybrid_avg": {"relevance": round(hyb_rel_avg, 2), "diversity": round(hyb_div_avg, 2)},
        "improvement": {
            "relevance": round(hyb_rel_avg - sem_rel_avg, 2),
            "diversity": round(hyb_div_avg - sem_div_avg, 2)
        },
        "categories": {}
    }
    
    for cat in ["learning", "emo", "running", "genre", "vague"]:
        cat_evals = [e for e in results["evaluations"] if e["category"] == cat]
        if cat_evals:
            cat_sem_rel = sum(e["semantic_only"]["evaluation"]["relevance"] for e in cat_evals) / len(cat_evals)
            cat_hyb_rel = sum(e["hybrid"]["evaluation"]["relevance"] for e in cat_evals) / len(cat_evals)
            results["summary"]["categories"][cat] = {
                "count": len(cat_evals),
                "semantic_avg_relevance": round(cat_sem_rel, 2),
                "hybrid_avg_relevance": round(cat_hyb_rel, 2),
                "improvement": round(cat_hyb_rel - cat_sem_rel, 2)
            }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Semantic-only avg: relevance={sem_rel_avg:.2f}, diversity={sem_div_avg:.2f}")
    print(f"Hybrid avg:        relevance={hyb_rel_avg:.2f}, diversity={hyb_div_avg:.2f}")
    print(f"Improvement:       relevance={hyb_rel_avg - sem_rel_avg:+.2f}, diversity={hyb_div_avg - sem_div_avg:+.2f}")
    print(f"\nResults saved to {output_path}")
    
    return results

if __name__ == "__main__":
    run_evaluation()