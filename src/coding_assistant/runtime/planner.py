import json
import logging
from typing import Any

from coding_assistant.routing.completion import RoutedCompletionService
from coding_assistant.routing.policy import infer_capability_and_complexity
from coding_assistant.runtime.types import AgentGraphState, PlannerOutput, StructuredAction
from coding_assistant.tools.registry import list_tools, openai_tool_specs

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a coding assistant runtime planner.

Rules:
- You NEVER output shell commands or bash. Only structured tool calls.
- Each action must use one of the registered tools with valid JSON arguments.
- When the task is complete, set finish=true and provide final_message.
- Prefer read-only tools (read_file, grep, search_code) before apply_patch.
- Request approval_request for destructive or sensitive operations.

Respond with JSON only matching this schema:
{
  "thought": "brief reasoning",
  "actions": [{"tool": "<tool_name>", "arguments": {...}}],
  "finish": false,
  "final_message": null
}
"""


class Planner:
    """Produces structured actions via capability-routed LiteLLM calls."""

    def __init__(self, completion: RoutedCompletionService | None = None) -> None:
        self._completion = completion or RoutedCompletionService()

    async def plan(self, state: AgentGraphState) -> PlannerOutput:
        capability, complexity = infer_capability_and_complexity(state)

        tools_desc = json.dumps(openai_tool_specs(), indent=2)
        definitions = list_tools()
        output_schemas = json.dumps(
            {t.name: t.output_schema for t in definitions},
            indent=2,
        )
        tool_results = state.get("tool_results") or []
        results_text = json.dumps([r.model_dump() for r in tool_results[-10:]], indent=2)

        user_content = (
            f"User request:\n{state['user_message']}\n\n"
            f"Workspace: {state['workspace_root']}\n"
            f"Iteration: {state['iteration']}/{state['max_iterations']}\n\n"
            f"Available tools (JSON Schema parameters):\n{tools_desc}\n\n"
            f"Expected output schemas:\n{output_schemas}\n\n"
            f"Recent tool results:\n{results_text}\n\n"
            "Produce the next planner JSON."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *state["messages"][-20:],
            {"role": "user", "content": user_content},
        ]

        try:
            result = await self._completion.complete(
                capability=capability,
                complexity=complexity,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                run_id=state.get("run_id"),
            )
            logger.info(
                "Planner routed capability=%s complexity=%s model=%s tier=%s",
                capability.value,
                complexity.value,
                result.route.model,
                result.route.tier,
            )
            data = json.loads(result.content or "{}")
            return _parse_planner_output(data)
        except Exception as exc:
            logger.exception("Planner LLM call failed")
            return PlannerOutput(
                thought="Planner failed; finishing with error.",
                finish=True,
                final_message=f"Planning failed: {exc}",
            )


def _parse_planner_output(data: dict[str, Any]) -> PlannerOutput:
    actions = []
    for item in data.get("actions") or []:
        if not isinstance(item, dict) or "tool" not in item:
            continue
        actions.append(
            StructuredAction(
                tool=item["tool"],
                arguments=item.get("arguments") or {},
            )
        )
    return PlannerOutput(
        thought=str(data.get("thought") or ""),
        actions=actions,
        finish=bool(data.get("finish")),
        final_message=data.get("final_message"),
    )
