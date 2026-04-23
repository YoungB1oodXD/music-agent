from __future__ import annotations
import logging
import time
from typing import Callable, Any
from src.evaluation.mock_data import get_test_queries

logger = logging.getLogger(__name__)


def benchmark_function(func: Callable, *args, **kwargs) -> tuple[Any, float]:
    """Run a function and return result and elapsed time in ms"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed


def benchmark_semantic_search(
    semantic_search_func: Callable, queries: list[str], top_k: int = 5
) -> dict:
    """Benchmark semantic search performance"""
    times = []
    for query in queries:
        _, elapsed = benchmark_function(semantic_search_func, query, top_k)
        times.append(elapsed)

    return {
        "operation": "semantic_search",
        "count": len(queries),
        "avg_ms": sum(times) / len(times) if times else 0,
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0,
    }


def run_benchmarks(semantic_func=None) -> dict:
    """Run all benchmarks and return summary"""
    results = {}

    if semantic_func:
        queries = get_test_queries()
        results["semantic"] = benchmark_semantic_search(semantic_func, queries[:5])

    logger.info(f"Benchmark results: {results}")
    return results
