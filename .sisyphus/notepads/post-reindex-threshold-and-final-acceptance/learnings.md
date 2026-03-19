# Learnings - Post-Reindex Threshold + Final Acceptance
Append-only.

## 2026-03-13: Threshold Recalibration
Recalibrated semantic search thresholds post-reindex to accommodate the new similarity distribution.
- `_MIN_SEMANTIC_SIMILARITY`: 0.31 -> 0.26
- `_HARD_MIN_SEMANTIC_SIMILARITY`: 0.30 -> 0.18

Rationale:
Post-reindex, top results for common queries like "学习" (0.259) and "emo" (0.295) were being pruned by the old 0.31/0.30 thresholds, leading to result collapse. The new thresholds ensure >1 results for these queries while still maintaining quality.
- 学习: count >= 5
- emo: count >= 5
- 夜跑: count >= 3

## 2026-03-13: Hybrid Threshold Alignment
Aligned `hybrid_recommend_tool.py` thresholds with `semantic_search_tool.py` to prevent over-pruning in hybrid results. This ensures that semantic candidates are not prematurely discarded before the hybrid scoring phase, maintaining recall consistency across tools.
  
## 2026-03-13: Evidence Report Generated  
Generated .sisyphus/evidence/post_reindex_threshold_tuning.md documenting the threshold recalibration. Verified that the new thresholds (0.26/0.18) successfully restored recall to 10 results for all test queries without compromising top-1 precision. 
"- Fixed basedpyright errors in src/tools/semantic_search_tool.py by implementing _coerce_similarity_to_float helper." 
