from fastapi import APIRouter

from coding_assistant.api.schemas import ToolDefinitionResponse
from coding_assistant.tools.registry import list_tools

router = APIRouter(prefix="/v1/tools", tags=["tools"])


@router.get("", response_model=list[ToolDefinitionResponse])
async def get_tools() -> list[ToolDefinitionResponse]:
    return [
        ToolDefinitionResponse(
            name=t.name,
            description=t.description,
            input_schema=t.input_schema,
            output_schema=t.output_schema,
        )
        for t in list_tools()
    ]
