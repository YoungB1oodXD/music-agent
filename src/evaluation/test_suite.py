from __future__ import annotations
import logging
from typing import List
from src.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    ndcg_at_k,
    coverage,
    diversity,
    novelty,
)

logger = logging.getLogger(__name__)


def test_precision_at_k():
    """Test precision_at_k calculation"""
    recommended = ["a", "b", "c", "d", "e"]
    relevant = {"a", "b", "c"}
    assert precision_at_k(recommended, relevant, 3) == 1.0
    assert precision_at_k(recommended, relevant, 5) == 0.6
    logger.info("test_precision_at_k passed")


def test_recall_at_k():
    """Test recall_at_k calculation"""
    recommended = ["a", "b", "c", "d", "e"]
    relevant = {"a", "b", "c", "d", "e"}
    assert recall_at_k(recommended, relevant, 3) == 0.6
    assert recall_at_k(recommended, relevant, 5) == 1.0
    logger.info("test_recall_at_k passed")


def test_ndcg_at_k():
    """Test NDCG calculation"""
    recommended = ["a", "b", "c"]
    relevant = {"a", "b"}
    result = ndcg_at_k(recommended, relevant, 3)
    assert 0.0 <= result <= 1.0
    logger.info("test_ndcg_at_k passed")


def test_coverage():
    """Test coverage calculation"""
    recommended = ["a", "b", "c"]
    total = {"a", "b", "c", "d", "e"}
    assert coverage(recommended, total) == 0.6
    logger.info("test_coverage passed")


def test_diversity():
    """Test diversity calculation"""
    recommended = ["a", "b", "c"]
    item_features = {
        "a": ["rock", "loud"],
        "b": ["jazz", "calm"],
        "c": ["pop", "dance"],
    }
    result = diversity(recommended, item_features)
    assert 0.0 <= result <= 1.0
    logger.info("test_diversity passed")


def test_novelty():
    """Test novelty calculation"""
    recommended = ["a", "b", "c"]
    popular = {"d", "e"}
    assert novelty(recommended, popular) == 1.0
    assert novelty(["a", "d"], popular) == 0.5
    logger.info("test_novelty passed")


def run_all_tests():
    """Run all evaluation tests"""
    tests = [
        test_precision_at_k,
        test_recall_at_k,
        test_ndcg_at_k,
        test_coverage,
        test_diversity,
        test_novelty,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"{test.__name__} failed: {e}")
    logger.info(f"Evaluation tests: {passed}/{len(tests)} passed")
    return passed, len(tests)


if __name__ == "__main__":
    run_all_tests()
