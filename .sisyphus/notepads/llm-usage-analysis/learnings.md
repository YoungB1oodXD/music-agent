# Learnings - LLM Usage Analysis
Append-only log of patterns, conventions, and successful approaches.
- [LLM Call Chain] /chat uses 2 calls (intent + final) with a JSON repair retry path in QwenClient.  
- [Token Drivers] History accumulation and RAG context are the primary drivers of prompt token growth.  
- [High Completion Tokens] Observed 4k+ completion tokens in probe, suggesting model verbosity or repetition issues. 
