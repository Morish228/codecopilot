from coding_assistant.runtime.types import AgentGraphState, ToolResult
from coding_assistant.routing.types import Capability, Complexity

READ_ONLY_TOOLS = frozenset({"read_file", "grep", "search_code"})
WRITE_TOOLS = frozenset({"apply_patch", "run_tests", "lint"})


def infer_capability_and_complexity(state: AgentGraphState) -> tuple[Capability, Complexity]:
    """Derive routing intent from graph state (no provider names)."""
    tool_results: list[ToolResult] = state.get("tool_results") or []
    iteration = state.get("iteration", 0)
    user_message = (state.get("user_message") or "").lower()

    if _recent_failures(tool_results):
        return Capability.FALLBACK, Complexity.LOW

    if _looks_like_debugging(user_message, tool_results):
        return Capability.DEBUGGING, Complexity.HIGH

    if _recent_used_tools(tool_results, WRITE_TOOLS):
        if "refactor" in user_message or "rename" in user_message or "extract" in user_message:
            return Capability.REFACTORING, Complexity.HIGH
        return Capability.CODING, Complexity.HIGH

    if iteration <= 1:
        return Capability.PLANNING, Complexity.HIGH

    if _recent_used_tools(tool_results, READ_ONLY_TOOLS) and not _recent_used_tools(
        tool_results, WRITE_TOOLS
    ):
        return Capability.FILE_SEARCH, Complexity.LOW

    return Capability.PLANNING, Complexity.MEDIUM


def _recent_failures(results: list[ToolResult], n: int = 5) -> bool:
    recent = results[-n:]
    return any(not r.success for r in recent)


def _recent_used_tools(results: list[ToolResult], names: frozenset[str], n: int = 5) -> bool:
    recent = results[-n:]
    return any(r.tool in names for r in recent)


def _looks_like_debugging(user_message: str, results: list[ToolResult]) -> bool:
    debug_terms = ("bug", "error", "fail", "exception", "traceback", "fix", "broken", "debug")
    if any(term in user_message for term in debug_terms):
        return True
    for r in results[-5:]:
        if r.tool == "run_tests" and not r.success:
            return True
        if r.error and ("fail" in r.error.lower() or "error" in r.error.lower()):
            return True
    return False
