#!/usr/bin/env python3
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.test_suite import run_all_tests
from src.evaluation.benchmark import run_benchmarks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    report_path = Path(__file__).parent.parent / "data" / "evaluation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Running evaluation tests...")
    passed, total = run_all_tests()

    logger.info("Running benchmarks...")
    benchmark_results = run_benchmarks()

    report = {
        "test_results": {
            "passed": passed,
            "total": total,
            "success_rate": passed / total if total > 0 else 0,
        },
        "benchmark_results": benchmark_results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Evaluation report saved to {report_path}")
    logger.info(f"Tests: {passed}/{total} passed")
    logger.info(f"Benchmarks: {benchmark_results}")

    return report


if __name__ == "__main__":
    main()
