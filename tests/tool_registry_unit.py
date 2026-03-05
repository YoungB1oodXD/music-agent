import os
import sys
from typing import cast

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.tools.registry import ToolRegistry


def _demo_handler(args: dict[str, object]) -> dict[str, object]:
    return {"ok": True, "data": {"message": f"{args['name']}:{args['count']}"}}


def run_tests() -> None:
    registry = ToolRegistry()

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["name", "count"],
    }

    registry.register(
        name="demo",
        description="demo tool",
        parameters_schema=schema,
        handler=_demo_handler,
    )

    ok_result: dict[str, object] = registry.dispatch("demo", {"name": "hello", "count": 2})
    assert ok_result["ok"] is True
    data = cast(dict[str, object], ok_result["data"])
    assert data["message"] == "hello:2"

    missing_required: dict[str, object] = registry.dispatch("demo", {"name": "hello"})
    assert missing_required["ok"] is False
    error = cast(str, missing_required["error"])
    assert "Missing required" in error

    unknown_arg: dict[str, object] = registry.dispatch("demo", {"name": "hello", "count": 1, "x": 1})
    assert unknown_arg["ok"] is False
    error = cast(str, unknown_arg["error"])
    assert "Unknown argument" in error

    invalid_type: dict[str, object] = registry.dispatch("demo", {"name": "hello", "count": "2"})
    assert invalid_type["ok"] is False
    error = cast(str, invalid_type["error"])
    assert "Invalid type" in error

    unknown_tool: dict[str, object] = registry.dispatch("not_exists", {})
    assert unknown_tool["ok"] is False
    error = cast(str, unknown_tool["error"])
    assert "Unknown tool" in error

    print("tool_registry_unit passed")


if __name__ == "__main__":
    run_tests()
