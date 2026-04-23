# AGENTS.md — RAG Layer
<!-- OMO_INTERNAL_INITIATOR -->

## OVERVIEW
Retrieval-Augmented Generation pipeline for building LLM prompt context from semantic music data.

## WHERE TO LOOK
- `retriever.py`: Fetches semantic docs using `MusicSearcher` via `semantic_search` tool. It maps raw search results to a standardized doc format.
- `context_builder.py`: Formats docs into a compact string for LLM consumption. It handles truncation if the context exceeds character limits.
- `sanitize.py`: Filters untrusted text to block prompt injection or system leaks. It checks for phrases like "ignore previous" or "system prompt".
- `src/config.py`: Contains global RAG settings like `RAG_RETRIEVAL_TOP_K` and `RAG_CONTEXT_MAX_CHARS`.

## CONVENTIONS
- **Tool-Layer Format**: Retrieval calls return `{"ok": bool, "data": object, "error": str | None}`. This matches the project's standard tool response.
- **Compact Formatting**: Use `[citation] artist=... title=...` style to save tokens. Avoid extra whitespace or descriptive labels.
- **Sanitization**: Run retrieved text through `sanitize_untrusted_text` before prompt insertion. This is non-negotiable for security.
- **Key Patterns**:
  - `_RAG_RETRIEVAL_TOP_K`: Default count for document fetching. Usually set to 5.
  - `_RAG_CONTEXT_MAX_CHARS`: Hard limit for context string length. Usually set to 1200.
- **Citation Style**: Every document needs a `[doc:N]` prefix for LLM attribution. The LLM uses these to cite its sources in the final response.
- **Field Mapping**: Only pass relevant fields like `artist`, `title`, and `genre` to the context builder.
- **Similarity Scores**: Include similarity scores in the context if available. They help the LLM gauge relevance.

## ANTI-PATTERNS
- **Raw Insertion**: Inserting retrieved text without sanitization is a security risk. It opens the door to prompt injection.
- **Token Waste**: Don't use verbose JSON or XML in context. Use the telegraphic line-based format instead.
- **Missing Citations**: Omitting citations makes it hard for the LLM to attribute sources. It leads to hallucinations.
- **Large K**: High `top_k` values dilute relevance and hit context limits. Stick to the default unless there's a strong reason.
- **Direct Searcher Calls**: Use the tool registry instead of calling searchers directly. This keeps the RAG layer decoupled from search implementation.
- **Ignoring Truncation**: Don't assume the context will fit. Always use `build_rag_context` to handle length limits gracefully.
- **Hardcoding Limits**: Don't hardcode character limits in the logic. Use the values from `src/config.py`.
