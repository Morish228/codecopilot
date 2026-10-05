from typing import Any

import jsonschema
from pydantic import BaseModel, ValidationError

from coding_assistant.tools.registry import get_registered_tool


class ToolValidationError(Exception):
    def __init__(self, tool_name: str, message: str, details: list | None = None) -> None:
        self.tool_name = tool_name
        self.details = details or []
        super().__init__(f"{tool_name}: {message}")


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> BaseModel:
    """Host-side validation before execution (Pydantic + JSON Schema)."""
    tool = get_registered_tool(tool_name)
    if tool is None:
        raise ToolValidationError(tool_name, "Unknown tool")

    definition = tool.definition()
    try:
        jsonschema.validate(instance=arguments, schema=definition.input_schema)
    except jsonschema.ValidationError as exc:
        raise ToolValidationError(tool_name, f"JSON Schema validation failed: {exc.message}") from exc

    try:
        return tool.input_model.model_validate(arguments)
    except ValidationError as exc:
        raise ToolValidationError(tool_name, "Pydantic validation failed", exc.errors()) from exc
