#!/usr/bin/env python3
"""
推荐效果评估脚本

评估混合推荐系统的效果，包括：
1. 标准指标评估 (Precision@K, Recall@K, NDCG@K)
2. 消融实验 (不同混合权重)
3. 多样性评估 (Genre/Tag Coverage, Intra-list Diversity)
4. 冷启动评估 (新用户/新歌曲)

输出: data/evaluation_report.json
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Any
from collections import defaultdict

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    ndcg_at_k,
    diversity as calc_diversity,
)
from src.tools.semantic_search_tool import semantic_search
from src.tools.hybrid_recommend_tool import hybrid_recommend


TEST_QUERIES = [
    {
        "query": "放松的爵士乐",
        "category": "genre",
        "expected_genres": ["Jazz"],
        "expected_tags": ["relaxed", "chill", "calm"],
    },
    {
        "query": "高能量的电子音乐",
        "category": "genre",
        "expected_genres": ["Electronic"],
        "expected_tags": ["energetic", "dance", "upbeat"],
    },
    {
        "query": "适合学习的音乐",
        "category": "scene",
        "expected_genres": [],
        "expected_tags": ["study", "concentration", "ambient"],
    },
    {
        "query": "深夜独处时听的歌",
        "category": "scene",
        "expected_genres": [],
        "expected_tags": ["night", "solo", "introspective"],
    },
    {
        "query": "健身时听的动感音乐",
        "category": "scene",
        "expected_genres": [],
        "expected_tags": ["workout", "energy", "upbeat"],
    },
    {
        "query": "摇滚乐",
        "category": "genre",
        "expected_genres": ["Rock"],
        "expected_tags": [],
    },
    {
        "query": "嘻哈音乐",
        "category": "genre",
        "expected_genres": ["Hip-Hop"],
        "expected_tags": [],
    },
    {
        "query": "民谣风格的歌",
        "category": "genre",
        "expected_genres": ["Folk"],
        "expected_tags": [],
    },
    {
        "query": "安静的钢琴曲",
        "category": "genre",
        "expected_genres": [],
        "expected_tags": ["piano", "quiet", "classical"],
    },
    {
        "query": "适合下雨天听的歌",
        "category": "scene",
        "expected_genres": [],
        "expected_tags": ["rain", "slow", "melancholy"],
    },
]

ABLATION_WEIGHTS = [
    {"w_sem": 1.0, "w_cf": 0.0, "name": "纯语义检索"},
    {"w_sem": 0.0, "w_cf": 1.0, "name": "纯内容匹配"},
    {"w_sem": 0.7, "w_cf": 0.3, "name": "混合(0.7:0.3)"},
    {"w_sem": 0.6, "w_cf": 0.4, "name": "混合(0.6:0.4)"},
    {"w_sem": 0.5, "w_cf": 0.5, "name": "混合(0.5:0.5)"},
]


def get_item_features(items: list[dict]) -> dict[str, list[str]]:
    """从搜索结果中提取物品特征"""
    features = {}
    for item in items:
        item_id = str(item.get("id") or item.get("track_id", ""))
        genre = str(item.get("genre") or "").lower()
        tags = item.get("mood_tags") or item.get("scene_tags") or []
        if isinstance(tags, list):
            tags = [str(t).lower() for t in tags]
        else:
            tags = []
        features[item_id] = [genre] + tags if genre else tags
    return features


def evaluate_results_list(
    items: list[dict], expected_genres: list[str], expected_tags: list[str], k: int
) -> dict[str, Any]:
    """评估一组推荐结果"""
    if not items:
        return {
            "count": 0,
            "genre_hits": 0,
            "tag_hits": 0,
            "genre_coverage": 0.0,
            "tag_coverage": 0.0,
            "avg_relevance": 0.0,
            "diversity": 0.0,
        }

    genres_found = set()
    tags_found = set()
    relevance_scores = []

    for item in items:
        if not isinstance(item, dict):
            continue

        genre = str(item.get("genre") or "").lower()
        if genre:
            genres_found.add(genre)

        item_tags = item.get("mood_tags") or item.get("scene_tags") or []
        if isinstance(item_tags, list):
            for tag in item_tags:
                tags_found.add(str(tag).lower())

        sim = float(item.get("similarity") or item.get("semantic_similarity") or 0)
        relevance_scores.append(sim)

    genre_hits = (
        sum(1 for g in expected_genres if any(g.lower() in gf for gf in genres_found))
        if expected_genres
        else 0
    )
    tag_hits = (
        sum(1 for t in expected_tags if any(t.lower() in tf for tf in tags_found))
        if expected_tags
        else 0
    )

    genre_coverage = genre_hits / len(expected_genres) if expected_genres else 1.0
    tag_coverage = tag_hits / len(expected_tags) if expected_tags else 1.0

    avg_relevance = (
        sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    )

    item_ids = [
        str(item.get("id") or item.get("track_id", ""))
        for item in items
        if isinstance(item, dict)
    ]
    item_features = get_item_features(items)
    diversity = calc_diversity(item_ids, item_features) if len(item_ids) > 1 else 1.0

    return {
        "count": len(items),
        "genre_hits": genre_hits,
        "tag_hits": tag_hits,
        "genre_coverage": round(genre_coverage, 3),
        "tag_coverage": round(tag_coverage, 3),
        "avg_relevance": round(avg_relevance, 3),
        "diversity": round(diversity, 3),
        "genres_found": list(genres_found),
        "tags_found": list(tags_found)[:10],
    }


def evaluate_single_query(
    query: str, expected_genres: list[str], expected_tags: list[str], k: int = 10
) -> dict[str, Any]:
    """评估单个查询的推荐效果"""
    results = {
        "query": query,
        "k": k,
        "semantic_only": {},
        "hybrid": {},
        "ablation": {},
    }

    sem_res = semantic_search({"query_text": query, "top_k": k})
    sem_items = sem_res.get("data", []) if sem_res.get("ok") else []
    results["semantic_only"] = evaluate_results_list(
        sem_items, expected_genres, expected_tags, k
    )

    hyb_res = hybrid_recommend(
        {
            "query_text": query,
            "seed_song_name": None,
            "top_k": k,
            "w_sem": 0.6,
            "w_cf": 0.4,
        }
    )
    hyb_items = hyb_res.get("data", []) if hyb_res.get("ok") else []
    results["hybrid"] = evaluate_results_list(
        hyb_items, expected_genres, expected_tags, k
    )

    for weights in ABLATION_WEIGHTS:
        if weights["w_sem"] == 0.6 and weights["w_cf"] == 0.4:
            continue
        if weights["w_sem"] == 1.0 and weights["w_cf"] == 0.0:
            continue
        if weights["w_sem"] == 0.0 and weights["w_cf"] == 1.0:
            continue

        ab_res = hybrid_recommend(
            {
                "query_text": query,
                "seed_song_name": None,
                "top_k": k,
                "w_sem": weights["w_sem"],
                "w_cf": weights["w_cf"],
            }
        )
        ab_items = ab_res.get("data", []) if ab_res.get("ok") else []
        results["ablation"][weights["name"]] = evaluate_results_list(
            ab_items, expected_genres, expected_tags, k
        )

    return results


def run_cold_start_evaluation(k: int = 10) -> dict[str, Any]:
    """评估冷启动场景"""
    cold_query = "放松的爵士乐"
    cold_start_results = {}

    res_no_seed = hybrid_recommend(
        {
            "query_text": cold_query,
            "seed_song_name": None,
            "top_k": k,
            "w_sem": 0.0,
            "w_cf": 1.0,
        }
    )
    items_no_seed = res_no_seed.get("data", []) if res_no_seed.get("ok") else []
    cold_start_results["new_user_no_history"] = evaluate_results_list(
        items_no_seed, ["Jazz"], ["relaxed", "chill"], k
    )

    res_with_seed = hybrid_recommend(
        {
            "query_text": cold_query,
            "seed_song_name": "Adelitas Way - Dirty Little Thing",
            "top_k": k,
            "w_sem": 0.6,
            "w_cf": 0.4,
        }
    )
    items_with_seed = res_with_seed.get("data", []) if res_with_seed.get("ok") else []
    cold_start_results["new_user_with_seed"] = evaluate_results_list(
        items_with_seed, ["Jazz"], ["relaxed", "chill"], k
    )

    cold_start_results["cold_songs"] = {
        "note": "新歌曲冷启动需要独立评估体系，本评估暂不覆盖"
    }

    return cold_start_results


def aggregate_metrics(all_results: list[dict]) -> dict[str, float]:
    """聚合多个查询的指标"""
    semantic_precisions = []
    semantic_ndcgs = []
    semantic_diversities = []
    hybrid_precisions = []
    hybrid_ndcgs = []
    hybrid_diversities = []

    for res in all_results:
        sem = res.get("semantic_only", {})
        hyb = res.get("hybrid", {})

        sem_precision = (
            sem.get("genre_coverage", 0) * 0.4 + sem.get("tag_coverage", 0) * 0.6
            if sem.get("count", 0) > 0
            else 0
        )
        hyb_precision = (
            hyb.get("genre_coverage", 0) * 0.4 + hyb.get("tag_coverage", 0) * 0.6
            if hyb.get("count", 0) > 0
            else 0
        )

        semantic_precisions.append(sem_precision)
        semantic_ndcgs.append(sem.get("avg_relevance", 0))
        semantic_diversities.append(sem.get("diversity", 0))
        hybrid_precisions.append(hyb_precision)
        hybrid_ndcgs.append(hyb.get("avg_relevance", 0))
        hybrid_diversities.append(hyb.get("diversity", 0))

    n = len(all_results) if all_results else 1

    return {
        "semantic_precision@10": round(sum(semantic_precisions) / n, 3),
        "semantic_ndcg@10": round(sum(semantic_ndcgs) / n, 3),
        "semantic_diversity@10": round(sum(semantic_diversities) / n, 3),
        "hybrid_precision@10": round(sum(hybrid_precisions) / n, 3),
        "hybrid_ndcg@10": round(sum(hybrid_ndcgs) / n, 3),
        "hybrid_diversity@10": round(sum(hybrid_diversities) / n, 3),
        "improvement_precision": round(
            (sum(hybrid_precisions) - sum(semantic_precisions)) / n, 3
        ),
        "improvement_ndcg": round((sum(hybrid_ndcgs) - sum(semantic_ndcgs)) / n, 3),
    }


def run_evaluation():
    """主评估流程"""
    output_dir = project_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "evaluation_report.json"

    print("=" * 60)
    print("推荐效果评估")
    print("=" * 60)

    all_results = []
    ablation_aggregated: dict[str, list] = defaultdict(list)

    for i, test_query in enumerate(TEST_QUERIES):
        print(f"\n[{i + 1}/{len(TEST_QUERIES)}] Query: {test_query['query']}")

        result = evaluate_single_query(
            test_query["query"],
            test_query["expected_genres"],
            test_query["expected_tags"],
            k=10,
        )
        result["category"] = test_query["category"]
        all_results.append(result)

        for ab_name, ab_res in result.get("ablation", {}).items():
            ablation_aggregated[ab_name].append(ab_res)

        sem = result["semantic_only"]
        hyb = result["hybrid"]
        print(
            f"  Semantic: prec={sem.get('genre_coverage', 0):.2f}, rel={sem.get('avg_relevance', 0):.3f}, div={sem.get('diversity', 0):.3f}"
        )
        print(
            f"  Hybrid:   prec={hyb.get('genre_coverage', 0):.2f}, rel={hyb.get('avg_relevance', 0):.3f}, div={hyb.get('diversity', 0):.3f}"
        )

    overall = aggregate_metrics(all_results)

    ablation_summary = {}
    for ab_name, ab_results in ablation_aggregated.items():
        if ab_results:
            avg_prec = sum(r.get("genre_coverage", 0) for r in ab_results) / len(
                ab_results
            )
            avg_rel = sum(r.get("avg_relevance", 0) for r in ab_results) / len(
                ab_results
            )
            avg_div = sum(r.get("diversity", 0) for r in ab_results) / len(ab_results)
            ablation_summary[ab_name] = {
                "precision@10": round(avg_prec, 3),
                "ndcg@10": round(avg_rel, 3),
                "diversity@10": round(avg_div, 3),
            }

    print("\n" + "=" * 60)
    print("消融实验结果")
    print("=" * 60)
    for ab_name, metrics in ablation_summary.items():
        print(
            f"  {ab_name}: prec={metrics['precision@10']:.3f}, ndcg={metrics['ndcg@10']:.3f}, div={metrics['diversity@10']:.3f}"
        )

    cold_start = run_cold_start_evaluation(k=10)

    category_results = {}
    for cat in ["genre", "scene"]:
        cat_results = [r for r in all_results if r.get("category") == cat]
        if cat_results:
            category_results[cat] = aggregate_metrics(cat_results)

    report = {
        "metadata": {
            "total_queries": len(TEST_QUERIES),
            "k": 10,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "overall_metrics": overall,
        "category_metrics": category_results,
        "ablation_study": ablation_summary,
        "cold_start_evaluation": cold_start,
        "detailed_results": all_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("总体结果")
    print("=" * 60)
    print(
        f"语义检索: Precision@10={overall['semantic_precision@10']:.3f}, NDCG@10={overall['semantic_ndcg@10']:.3f}"
    )
    print(
        f"混合推荐: Precision@10={overall['hybrid_precision@10']:.3f}, NDCG@10={overall['hybrid_ndcg@10']:.3f}"
    )
    print(
        f"提升:     Precision@10={overall['improvement_precision']:+.3f}, NDCG@10={overall['improvement_ndcg']:+.3f}"
    )
    print(f"\n报告已保存至: {output_path}")

    return report


if __name__ == "__main__":
    run_evaluation()
