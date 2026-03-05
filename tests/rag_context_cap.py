import importlib.util
from pathlib import Path
from typing import Protocol, cast


class BuildRagContext(Protocol):
    def __call__(self, docs: list[dict[str, object]], max_chars: int = 2000) -> str: ...


def load_context_builder() -> BuildRagContext:
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "src" / "rag" / "context_builder.py"
    module_spec = importlib.util.spec_from_file_location("rag_context_builder", module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Failed to load context builder module: {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    builder_obj = getattr(module, "build_rag_context", None)
    if not callable(builder_obj):
        raise RuntimeError("build_rag_context is missing")
    return cast(BuildRagContext, builder_obj)


def main() -> None:
    build_rag_context = load_context_builder()

    docs: list[dict[str, object]] = []
    repeated_text = "x" * 220
    for index in range(40):
        docs.append(
            {
                "doc_id": index,
                "artist": f"Artist {index} {repeated_text}",
                "title": f"Title {index} {repeated_text}",
                "genre": "ambient",
                "tags": ["focus", index, "instrumental"],
                "similarity": 0.12345,
            }
        )

    context = build_rag_context(docs, max_chars=2000)

    assert len(context) <= 2000, f"Context exceeded hard cap: {len(context)}"
    assert len(context) <= 2100, f"Context unexpectedly long: {len(context)}"
    assert context.startswith("[doc:0] artist=Artist 0"), context
    assert "tags=focus, 0, instrumental" in context, context
    assert "similarity=0.123" in context, context


if __name__ == "__main__":
    main()
