# Decisions - Recommendation Authenticity
Append-only log of architectural choices and rationales.
## 2026-03-07: Decision on RecommendationRecord.results Type 
- Chose to use a typed structure (RecommendationItem) for results to ensure consistency and provide rich fields (id, name, reason, citations). 
- Decided to keep the field name as 'results' to match existing code, but added compatibility methods to avoid breaking the orchestrator. 
- Decided to handle ID extraction in add_feedback to support passing rich objects directly. 
