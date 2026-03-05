from typing import Callable, TypedDict, cast


JSON = dict[str, object]
Schema = dict[str, object]
Handler = Callable[[JSON], JSON]


class ToolSpec(TypedDict):
    name: str
    description: str
    parameters_schema: Schema
    handler: Handler


class ToolRegistry:

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: object,
        handler: object,
    ) -> None:
        if not name:
            raise ValueError("Tool name cannot be empty")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if not isinstance(parameters_schema, dict):
            raise TypeError("parameters_schema must be a dict")

        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters_schema": cast(Schema, parameters_schema),
            "handler": cast(Handler, handler),
        }

    def list_tools(self) -> dict[str, JSON]:
        return {
            name: {
                "name": spec["name"],
                "description": spec["description"],
                "parameters_schema": spec["parameters_schema"],
            }
            for name, spec in self._tools.items()
        }

    def dispatch(self, name: str, args: object) -> JSON:
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "data": None, "error": f"Unknown tool: {name}"}

        try:
            validated = self._validate_args(tool["parameters_schema"], args)
        except (TypeError, ValueError) as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        handler = tool["handler"]
        try:
            result = handler(validated)
        except Exception as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        if "ok" in result and "data" in result:
            return result
        return {"ok": True, "data": result}

    def _validate_args(self, schema: Schema, args: object) -> JSON:
        if not isinstance(args, dict):
            raise TypeError("Tool args must be an object")

        properties_obj = schema.get("properties", {})
        required_obj = schema.get("required", [])

        if not isinstance(properties_obj, dict):
            raise TypeError("Schema 'properties' must be a dict")
        if not isinstance(required_obj, list):
            raise TypeError("Schema 'required' must be a list")
        required_values = cast(list[object], required_obj)
        if not all(isinstance(key, str) for key in required_values):
            raise TypeError("Schema 'required' must contain strings")

        properties = cast(JSON, properties_obj)
        required = [key for key in required_values if isinstance(key, str)]
        normalized_args = cast(JSON, args)

        unknown = [key for key in normalized_args if key not in properties]
        if unknown:
            raise ValueError(f"Unknown argument(s): {', '.join(unknown)}")

        missing = [key for key in required if key not in normalized_args]
        if missing:
            raise ValueError(f"Missing required argument(s): {', '.join(missing)}")

        for key, value in normalized_args.items():
            property_schema = properties.get(key)
            expected_type: str | None = None
            if isinstance(property_schema, dict):
                property_schema_dict = cast(JSON, property_schema)
                expected_type_obj = property_schema_dict.get("type")
                if isinstance(expected_type_obj, str):
                    expected_type = expected_type_obj

            if expected_type and not self._matches_type(expected_type, value):
                actual = type(value).__name__
                raise TypeError(
                    f"Invalid type for '{key}': expected {expected_type}, got {actual}"
                )

        return normalized_args

    @staticmethod
    def _matches_type(expected_type: str, value: object) -> bool:
        type_map: dict[str, Callable[[object], bool]] = {
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
        }
        checker = type_map.get(expected_type)
        if checker is None:
            return True
        return checker(value)
