from __future__ import annotations

def _stringify_similarity(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _format_doc_line(doc: dict[str, object], index: int) -> str:
    citation_raw = doc.get("citation")
    if isinstance(citation_raw, str) and citation_raw.strip():
        citation = citation_raw.strip()
    else:
        citation = f"doc:{doc.get('doc_id', index)}"

    parts: list[str] = [f"[{citation}]"]

    for key in ("artist", "title", "genre"):
        value = doc.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(f"{key}={text}")

    similarity_raw = doc.get("similarity")
    if similarity_raw is not None:
        similarity = _stringify_similarity(similarity_raw).strip()
        if similarity:
            parts.append(f"sim={similarity}")

    return " ".join(parts)


def build_rag_context(docs: list[dict[str, object]], max_chars: int = 2000) -> str:
    if max_chars <= 0:
        return ""

    chunks: list[str] = []
    used_chars = 0

    for index, doc in enumerate(docs):
        line = _format_doc_line(doc, index)
        candidate = f"{line}\n"
        candidate_len = len(candidate)

        if used_chars + candidate_len <= max_chars:
            chunks.append(candidate)
            used_chars += candidate_len
            continue

        if used_chars == 0:
            remaining = max_chars - used_chars
            if remaining > 0:
                chunks.append(candidate[:remaining])
        break

    return "".join(chunks)
