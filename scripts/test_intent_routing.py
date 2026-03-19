#!/usr/bin/env python3
import os
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.hybrid_recommend_tool import hybrid_recommend, _get_intent_weights, _compute_cf_signal_strength

INTENT_TESTS = [
    {"intent": "search", "expected_weights": (1.0, 0.0), "desc": "search -> semantic-only"},
    {"intent": "recommend", "expected_weights": (0.7, 0.3), "desc": "recommend -> balanced (when CF strong)"},
    {"intent": "similar_to_last", "expected_weights": (0.4, 0.6), "desc": "similar_to_last -> CF-prioritized (when CF strong)"},
]

def test_intent_routing():
    print("=" * 60)
    print("INTENT ROUTING TESTS")
    print("=" * 60)
    
    passed = 0
    total = len(INTENT_TESTS)
    
    cf_signal_strong = {"mean": 0.5, "spread": 0.3, "max": 0.8}
    cf_signal_weak = {"mean": 1e-10, "spread": 1e-11, "max": 1e-9}
    
    for test in INTENT_TESTS:
        intent = test["intent"]
        expected = test["expected_weights"]
        desc = test["desc"]
        
        result_strong = _get_intent_weights(intent, cf_signal_strong)
        result_weak = _get_intent_weights(intent, cf_signal_weak)
        
        print(f"\nIntent: {intent}")
        print(f"  Description: {desc}")
        print(f"  Strong CF signal: {result_strong}")
        print(f"  Weak CF signal: {result_weak}")
        
        if result_weak == (1.0, 0.0):
            print(f"  [PASS] Weak CF correctly falls back to semantic-only")
            passed += 1
        else:
            print(f"  [FAIL] Weak CF did not fallback correctly")
        
        if result_strong == expected:
            print(f"  [PASS] Strong CF uses correct intent weights")
            passed += 1
        else:
            print(f"  [FAIL] Expected {expected}, got {result_strong}")
    
    print(f"\n{'=' * 60}")
    print(f"PASSED: {passed}/{total * 2}")
    print("=" * 60)
    
    return passed == total * 2

if __name__ == "__main__":
    success = test_intent_routing()
    sys.exit(0 if success else 1)