from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def precision_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Precision@K: proportion of recommended items that are relevant"""
    if k <= 0:
        return 0.0
    recommended_k = recommended[:k]
    if not recommended_k:
        return 0.0
    hits = sum(1 for item in recommended_k if item in relevant)
    return hits / len(recommended_k)


def recall_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Recall@K: proportion of relevant items that are recommended"""
    if k <= 0 or not relevant:
        return 0.0
    recommended_k = recommended[:k]
    if not recommended_k:
        return 0.0
    hits = sum(1 for item in recommended_k if item in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K"""
    if k <= 0:
        return 0.0
    recommended_k = recommended[:k]
    if not recommended_k:
        return 0.0

    dcg = 0.0
    for i, item in enumerate(recommended_k):
        if item in relevant:
            dcg += 1.0 / (i + 1)

    idcg = sum(1.0 / (i + 1) for i in range(min(len(relevant), k)))

    if idcg == 0:
        return 0.0
    return dcg / idcg


def coverage(recommended_items: list[str], total_items: set[str]) -> float:
    """Coverage: proportion of total items that can be recommended"""
    if not total_items:
        return 0.0
    recommended_set = set(recommended_items)
    return len(recommended_set & total_items) / len(total_items)


def diversity(recommended: list[str], item_features: dict[str, list[str]]) -> float:
    """Diversity: measure of variety in recommended items based on features"""
    if len(recommended) <= 1:
        return 1.0

    total_similarity = 0.0
    pairs = 0
    for i in range(len(recommended)):
        for j in range(i + 1, len(recommended)):
            item_i_features = set(item_features.get(recommended[i], []))
            item_j_features = set(item_features.get(recommended[j], []))
            if not item_i_features or not item_j_features:
                continue
            intersection = len(item_i_features & item_j_features)
            union = len(item_i_features | item_j_features)
            similarity = intersection / union if union > 0 else 0.0
            total_similarity += similarity
            pairs += 1

    if pairs == 0:
        return 1.0
    avg_similarity = total_similarity / pairs
    return 1.0 - avg_similarity


def novelty(recommended: list[str], popular_items: set[str]) -> float:
    """Novelty: how novel are the recommendations (inverse of popularity)"""
    if not recommended:
        return 0.0
    novel_count = sum(1 for item in recommended if item not in popular_items)
    return novel_count / len(recommended)
