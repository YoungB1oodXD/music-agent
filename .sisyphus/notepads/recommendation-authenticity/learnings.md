# Learnings - Recommendation Authenticity
Append-only log of patterns, conventions, and successful approaches.
## 2026-03-07: Rich Recommendation Objects in Session State 
- Updated RecommendationRecord to store rich objects (RecommendationItem) instead of just strings. 
- Implemented backward compatibility in RecommendationItem by adding a strip() method and __str__(), allowing it to be used where strings are expected (e.g., in orchestrator's _merge_ids). 
- Updated add_recommendation and add_feedback to handle both strings and rich objects robustly. 

- Orchestrator.handle_turn now returns a dictionary with assistant_text and recommendations.  
- SessionState.add_recommendation is now called with rich recommendation objects (dicts) instead of just IDs.  
- RecommendationItem in SessionState supports compatibility with string-like operations via strip() and __str__(), but explicit ID extraction is safer for type checking. 
- Fixed feedback target_id extraction in Orchestrator to use .id when accessing RecommendationItem objects from SessionState. 
"Updated src/api/app.py to return rich RecommendationObject from /chat endpoint. Handled backward compatibility for orchestrator return types." 
- Updated `tests/api_chat_smoke.py` to assert the new rich object structure in the `/chat` response.  
- Verified that recommendations now include `id`, `name`, `reason`, and `citations`. 
  
## Grounding Rule Enhancement (2026-03-08)  
- Enhanced `_generate_final_response` prompt in `src/agent/orchestrator.py` to enforce grounding.  
- Added explicit instructions to use `tool_results` or `rag_context` for `reason` and `citations`.  
- Forbidden generic "与当前需求匹配" reasons.  
- Instructed model to use specific evidence identifiers in `citations`. 

## Frontend Mapping Update (2026-03-08)
- Updated `frontend/src/mappers/recommendations_to_tracks.ts` to map rich recommendation objects to `Track` interface.
- Implemented parsing of `"Artist - Title"` format from `name` field into separate `artist` and `title` fields.
- Added Chinese fallback reason "基于您的听歌偏好推荐" for recommendations without a specific reason.
- Mapped `citations` to `Track.tags` (capped to 3) to display them as chips in the UI.
- Maintained backward compatibility for string-based recommendations.
- Added automatic scaling for `matchScore` if the input score is in the 0-1 range.

  
## Grounding Seed Recommendations  
- Captured full tool result rows in `_extract_recommendations` and `_build_recommendations_from_rows`.  
- Updated `_build_seed_recommendations` to generate grounded `reason` and `citations` based on tool-specific fields (similarity, score, genre, sources).  
- This ensures that even in mock mode or LLM fallback, recommendations are presented with concrete evidence from the retrieval tools.  
- Citation format: `tool_name.field=value` (e.g., `semantic_search.similarity=0.92`). 
