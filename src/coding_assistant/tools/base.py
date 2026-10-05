from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from coding_assistant.tools.schema_builder import strict_json_schema
from coding_assistant.tools.schemas import ToolDefinition

HandlerFn = Callable[[Path, BaseModel], Awaitable[BaseModel]]


@dataclass(frozen=True)
class RegisteredTool:
    """A schema-driven tool with validated input/output."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: HandlerFn

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=strict_json_schema(self.input_model),
            output_schema=strict_json_schema(self.output_model),
        )

    async def execute(self, workspace_root: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        from coding_assistant.tools.outputs import serialize_output

        validated = self.input_model.model_validate(arguments)
        output = await self.handler(workspace_root, validated)
        if not isinstance(output, self.output_model):
            output = self.output_model.model_validate(output)
        return serialize_output(output)
