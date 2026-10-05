from coding_assistant.runtime.types import AgentGraphState, PlannerOutput


class ResponseGenerator:
    """Synthesizes the final user-facing response from planner output and tool results."""

    def generate(self, state: AgentGraphState, planner_output: PlannerOutput | None) -> str:
        if state.get("final_response"):
            return state["final_response"]

        if planner_output and planner_output.final_message:
            return planner_output.final_message

        if planner_output and planner_output.thought:
            base = planner_output.thought
        else:
            base = "Task completed."

        results = state.get("tool_results") or []
        if not results:
            return base

        summaries: list[str] = []
        for r in results[-5:]:
            if r.success:
                summaries.append(f"- {r.tool}: OK")
            else:
                summaries.append(f"- {r.tool}: {r.error or 'failed'}")

        return f"{base}\n\nTool summary:\n" + "\n".join(summaries)
