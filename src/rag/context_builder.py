from __future__ import annotations

from typing import cast


def _stringify_tags(value: object) -> str:
    if isinstance(value, list):
        items = cast(list[object], value)
        return ", ".join(str(item) for item in items)
    return str(value)


def _stringify_similarity(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _format_doc_line(doc: dict[str, object], index: int) -> str:
    doc_id_raw = doc.get("doc_id", doc.get("id", index))
    artist_raw = doc.get("artist", "")
    title_raw = doc.get("title", "")
    genre_raw = doc.get("genre", "")
    tags_raw = doc.get("tags", "")
    similarity_raw = doc.get("similarity", "")

    doc_id = str(doc_id_raw)
    artist = str(artist_raw)
    title = str(title_raw)
    genre = str(genre_raw)
    tags = _stringify_tags(tags_raw)
    similarity = _stringify_similarity(similarity_raw)

    return (
        f"[doc:{doc_id}] "
        f"artist={artist} "
        f"title={title} "
        f"genre={genre} "
        f"tags={tags} "
        f"similarity={similarity}"
    )


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
