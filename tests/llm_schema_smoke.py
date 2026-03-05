# -*- coding: utf-8 -*-
import sys
import os

from typing import cast

# 将 src 目录添加到 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.llm.prompts.schemas import INTENT_AND_SLOTS_SCHEMA, FINAL_RESPONSE_SCHEMA
    print("Successfully imported schemas.")
except ImportError as e:
    print(f"Failed to import schemas: {e}")
    sys.exit(1)

def test_schema_structure(schema: dict[str, object], name: str) -> bool:
    if "type" not in schema or schema["type"] != "object":
        print(f"Error: {name} must be an object type.")
        return False
    if "properties" not in schema:
        print(f"Error: {name} missing 'properties'.")
        return False
    
    props = cast(dict[str, dict[str, object]], schema["properties"])
    if name == "INTENT_AND_SLOTS_SCHEMA":
        required_keys = ["intent", "query_text"]
        for key in required_keys:
            if key not in props:
                print(f"Error: {name} missing required property '{key}'.")
                return False
        intent_enum = cast(list[str], props["intent"].get("enum", []))
        expected_intents = ["recommend_music", "search_music", "refine_preferences", "explain_why", "feedback"]
        if not all(i in intent_enum for i in expected_intents):
            print(f"Error: {name} intent enum is missing expected values.")
            return False
            
    elif name == "FINAL_RESPONSE_SCHEMA":
        required_keys = ["assistant_text", "recommendations"]
        for key in required_keys:
            if key not in props:
                print(f"Error: {name} missing required property '{key}'.")
                return False
        if props["recommendations"].get("type") != "array":
            print(f"Error: {name} 'recommendations' must be an array.")
            return False

    print(f"{name} structure is valid.")
    return True

if __name__ == "__main__":
    success = True
    success &= test_schema_structure(cast(dict[str, object], INTENT_AND_SLOTS_SCHEMA), "INTENT_AND_SLOTS_SCHEMA")
    success &= test_schema_structure(cast(dict[str, object], FINAL_RESPONSE_SCHEMA), "FINAL_RESPONSE_SCHEMA")
    
    if success:
        print("All schema smoke tests passed.")
        sys.exit(0)
    else:
        print("Some schema smoke tests failed.")
        sys.exit(1)
