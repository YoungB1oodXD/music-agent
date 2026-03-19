from __future__ import annotations

from typing import cast

from src.tools.semantic_search_tool import semantic_search


_PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "artist",
    "title",
    "genre",
    "similarity",
)


def retrieve_semantic_docs(query_text: str, top_k: int) -> list[dict[str, object]]:
    result = semantic_search({"query_text": query_text, "top_k": top_k})
    if result.get("ok") is not True:
        return []

    data_raw = result.get("data")
    if not isinstance(data_raw, list):
        return []
    data = cast(list[object], data_raw)

    docs: list[dict[str, object]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue

        source = cast(dict[str, object], item)
        doc: dict[str, object] = {
            "citation": f"doc:{index}",
            "doc_id": index,
        }
        for field in _PASSTHROUGH_FIELDS:
            value = source.get(field)
            if value is not None:
                doc[field] = value
        docs.append(doc)

    return docs
