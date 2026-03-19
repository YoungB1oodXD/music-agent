#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Score Normalization Audit
Verifies that semantic and CF scores are combined correctly.
"""

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
from src.tools.cf_recommend_tool import cf_recommend
from src.tools.hybrid_recommend_tool import hybrid_recommend, _normalize_scores, _to_float
from src.recommender.music_recommender import MusicRecommender


def run_audit():
    output_path = project_root / ".sisyphus" / "tmp" / "hybrid_score_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    queries = [
        "我想听适合学习的轻音乐",
        "我现在有点emo，想听安静一点的歌",
        "来点适合夜跑的高能量音乐"
    ]
    
    # Get a seed song for CF
    recommender = MusicRecommender()
    seed_id = next(iter(recommender.item_to_internal))
    seed_name = recommender.metadata.get(seed_id, seed_id)
    
    results = {
        "seed_song": seed_name,
        "queries": {}
    }
    
    for q in queries:
        query_key = q[:10] + "..." if len(q) > 10 else q
        query_result = {}
        
        # Semantic raw
        sem_res = semantic_search({'query_text': q, 'top_k': 20})
        sem_items = sem_res.get('data', []) if sem_res.get('ok') else []
        sem_scores = [_to_float(item.get('similarity', 0)) for item in sem_items if isinstance(item, dict)]
        
        query_result["semantic"] = {
            "ok": sem_res.get('ok'),
            "count": len(sem_items),
            "raw_min": min(sem_scores) if sem_scores else 0,
            "raw_max": max(sem_scores) if sem_scores else 0,
        }
        
        # CF raw (using seed song)
        cf_res = cf_recommend({'song_name': seed_name, 'top_k': 20})
        cf_data = cf_res.get('data', {}) if cf_res.get('ok') else {}
        cf_recs = cf_data.get('recommendations', []) if isinstance(cf_data, dict) else []
        cf_scores = [_to_float(rec.get('score', 0)) for rec in cf_recs if isinstance(rec, dict)]
        
        query_result["cf"] = {
            "ok": cf_res.get('ok'),
            "count": len(cf_recs),
            "raw_min": min(cf_scores) if cf_scores else 0,
            "raw_max": max(cf_scores) if cf_scores else 0,
        }
        
        # Hybrid result
        hyb_res = hybrid_recommend({
            'query_text': q,
            'seed_song_name': seed_name,
            'top_k': 10,
            'w_sem': 0.6,
            'w_cf': 0.4
        })
        hyb_items = hyb_res.get('data', []) if hyb_res.get('ok') else []
        hyb_scores = [_to_float(item.get('score', 0)) for item in hyb_items if isinstance(item, dict)]
        hyb_sem = [_to_float(item.get('semantic_similarity') or 0) for item in hyb_items if isinstance(item, dict)]
        hyb_cf = [_to_float(item.get('cf_score') or 0) for item in hyb_items if isinstance(item, dict)]
        sources_list = [item.get('sources', []) for item in hyb_items if isinstance(item, dict)]
        
        query_result["hybrid"] = {
            "ok": hyb_res.get('ok'),
            "count": len(hyb_items),
            "score_min": min(hyb_scores) if hyb_scores else 0,
            "score_max": max(hyb_scores) if hyb_scores else 0,
            "semantic_in_output_min": min(hyb_sem) if hyb_sem else 0,
            "semantic_in_output_max": max(hyb_sem) if hyb_sem else 0,
            "cf_in_output_min": min([s for s in hyb_cf if s > 0], default=0),
            "cf_in_output_max": max(hyb_cf) if any(hyb_cf) else 0,
            "sources_sample": sources_list[:3]
        }
        
        results["queries"][q] = query_result
    
    # Normalization check
    print("=== Normalization Check ===")
    test_sem = [{'id': f't{i}', 'score': 0.3 + i*0.02} for i in range(10)]
    test_cf_small = [{'id': f't{i}', 'score': 1e-9 + i*1e-10} for i in range(10)]
    test_cf_neg = [{'id': f't{i}', 'score': -0.5 + i*0.1} for i in range(10)]
    
    sem_norm = _normalize_scores(test_sem, 'score')
    cf_small_norm = _normalize_scores(test_cf_small, 'score')
    cf_neg_norm = _normalize_scores(test_cf_neg, 'score')
    
    results["normalization_test"] = {
        "semantic_0_3_to_0_5": {
            "normalized_min": min(sem_norm.values()),
            "normalized_max": max(sem_norm.values())
        },
        "cf_very_small_1e9_range": {
            "normalized_min": min(cf_small_norm.values()),
            "normalized_max": max(cf_small_norm.values())
        },
        "cf_negative_range": {
            "normalized_min": min(cf_neg_norm.values()),
            "normalized_max": max(cf_neg_norm.values())
        }
    }
    
    # Cold start test
    q_test = queries[0]
    hyb_no_cf = hybrid_recommend({'query_text': q_test, 'top_k': 10})
    hyb_no_cf_items = hyb_no_cf.get('data', []) if hyb_no_cf.get('ok') else []
    sources_no_cf = [item.get('sources', []) for item in hyb_no_cf_items if isinstance(item, dict)]
    
    results["cold_start_test"] = {
        "query": q_test,
        "count": len(hyb_no_cf_items),
        "sources_sample": sources_no_cf[:3]
    }
    
    # Write results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to {output_path}")
    
    # Print summary
    print("\n=== Summary ===")
    for q, data in results["queries"].items():
        print(f"\nQuery: {q[:20]}...")
        print(f"  Semantic: count={data['semantic']['count']}, range=[{data['semantic']['raw_min']:.4f}, {data['semantic']['raw_max']:.4f}]")
        print(f"  CF: count={data['cf']['count']}, range=[{data['cf']['raw_min']:.10f}, {data['cf']['raw_max']:.10f}]")
        print(f"  Hybrid: count={data['hybrid']['count']}, final_score=[{data['hybrid']['score_min']:.4f}, {data['hybrid']['score_max']:.4f}]")
        print(f"  Sources: {data['hybrid']['sources_sample']}")
    
    print("\n=== Normalization Test ===")
    norm = results["normalization_test"]
    print(f"Semantic [0.3, 0.5] -> [{norm['semantic_0_3_to_0_5']['normalized_min']:.4f}, {norm['semantic_0_3_to_0_5']['normalized_max']:.4f}]")
    print(f"CF small [~1e-9] -> [{norm['cf_very_small_1e9_range']['normalized_min']:.10f}, {norm['cf_very_small_1e9_range']['normalized_max']:.10f}]")
    print(f"CF negative -> [{norm['cf_negative_range']['normalized_min']:.4f}, {norm['cf_negative_range']['normalized_max']:.4f}]")
    
    return results


if __name__ == "__main__":
    run_audit()