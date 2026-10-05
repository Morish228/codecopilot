import logging
import uuid
from typing import Literal

from langgraph.graph import END, StateGraph

from coding_assistant.observability.metrics import record_run_started
from coding_assistant.observability.tracing import traced_span
from coding_assistant.runtime.approval_manager import ApprovalManager
from coding_assistant.runtime.planner import Planner
from coding_assistant.runtime.response_generator import ResponseGenerator
from coding_assistant.runtime.state_manager import StateManager
from coding_assistant.runtime.tool_executor import ToolExecutor
from coding_assistant.runtime.types import AgentGraphState, initial_state

logger = logging.getLogger(__name__)

_planner = Planner()
_tool_executor = ToolExecutor()
_response_generator = ResponseGenerator()


async def _planner_node(state: AgentGraphState) -> AgentGraphState:
    iteration = state["iteration"] + 1
    if iteration > state["max_iterations"]:
        return {
            **state,
            "iteration": iteration,
            "status": "failed",
            "error": "Max iterations exceeded",
        }

    async with traced_span("agent.planning", {"run.id": state.get("run_id")}):
        output = await _planner.plan(state)
    new_messages = list(state["messages"])
    if output.thought:
        new_messages.append({"role": "assistant", "content": output.thought})

    return {
        **state,
        "iteration": iteration,
        "planner_output": output,
        "messages": new_messages,
    }


async def _execute_tools_node(state: AgentGraphState) -> AgentGraphState:
    planner_output = state.get("planner_output")
    if not planner_output or not planner_output.actions:
        return state

    async with traced_span("agent.tool_calls", {"run.id": state.get("run_id")}):
        _, updated = await _tool_executor.execute_actions(state, planner_output.actions)
    return updated


async def _respond_node(state: AgentGraphState) -> AgentGraphState:
    planner_output = state.get("planner_output")
    if state.get("status") == "failed" and state.get("error"):
        final = state.get("error") or "Run failed."
    else:
        final = _response_generator.generate(state, planner_output)

    async with traced_span("agent.final_output", {"run.id": state.get("run_id")}):
        return {
            **state,
            "final_response": final,
            "status": "completed",
            "messages": [*state["messages"], {"role": "assistant", "content": final}],
        }


def _route_after_planner(state: AgentGraphState) -> Literal["execute_tools", "respond"]:
    if state.get("status") == "failed":
        return "respond"
    planner_output = state.get("planner_output")
    if planner_output and planner_output.finish:
        return "respond"
    if planner_output and planner_output.actions:
        return "execute_tools"
    return "respond"


def _route_after_execute(state: AgentGraphState) -> Literal["planner", "respond", "__end__"]:
    if state.get("pending_approval"):
        return "__end__"
    if state.get("status") == "failed":
        return "respond"
    if state["iteration"] >= state["max_iterations"]:
        return "respond"
    planner_output = state.get("planner_output")
    if planner_output and planner_output.finish:
        return "respond"
    return "planner"


def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentGraphState)
    graph.add_node("planner", _planner_node)
    graph.add_node("execute_tools", _execute_tools_node)
    graph.add_node("respond", _respond_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"execute_tools": "execute_tools", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "execute_tools",
        _route_after_execute,
        {"planner": "planner", "respond": "respond", "__end__": END},
    )
    graph.add_edge("respond", END)
    return graph


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph().compile()
    return _compiled_graph


class AgentRuntime:
    """Orchestrates LangGraph execution with persistence and approval gates."""

    def __init__(self, state_manager: StateManager, approval_manager: ApprovalManager) -> None:
        self._state_manager = state_manager
        self._approval_manager = approval_manager

    async def run(
        self,
        run_id: uuid.UUID,
        workspace_root: str,
        user_message: str,
        max_iterations: int,
    ) -> AgentGraphState:
        record_run_started()
        state = initial_state(
            run_id=str(run_id),
            workspace_root=workspace_root,
            user_message=user_message,
            max_iterations=max_iterations,
        )
        async with traced_span(
            "agent.run",
            {"run.id": str(run_id), "workspace.root": workspace_root},
        ):
            graph = get_compiled_graph()
            final_state: AgentGraphState = await graph.ainvoke(state)

        final_state = await self._finalize_approval(run_id, final_state)
        await self._persist_run(run_id, final_state, checkpoint_step="run_complete")
        return final_state

    async def resume_after_approval(
        self,
        run_id: uuid.UUID,
        approval_id: uuid.UUID,
        approved: bool,
    ) -> AgentGraphState | None:
        record = await self._approval_manager.get_pending(run_id, approval_id)
        if record is None:
            return None

        loaded = await self._state_manager.load_graph_state(str(run_id))
        if loaded is None:
            return None

        await self._approval_manager.resolve(approval_id, approved)
        cleared = self._approval_manager.clear_pending(loaded, approved)
        await self._state_manager.persist_graph_state(
            str(run_id), cleared, checkpoint_step="approval_decision"
        )

        if not approved:
            return cleared

        deferred = self._approval_manager.deferred_action_from_pending(
            loaded.get("pending_approval")
        ) or self._approval_manager.deferred_action_from_record(record)

        if deferred:
            _, cleared = await _tool_executor.execute_actions(
                cleared, [deferred], bypass_approval=True
            )
            await self._persist_run(run_id, cleared, checkpoint_step="post_approval_execute")

        graph = get_compiled_graph()
        final_state: AgentGraphState = await graph.ainvoke(cleared)
        final_state = await self._finalize_approval(run_id, final_state)
        await self._persist_run(run_id, final_state, checkpoint_step="run_complete")
        return final_state

    async def _finalize_approval(
        self, run_id: uuid.UUID, state: AgentGraphState
    ) -> AgentGraphState:
        pending = state.get("pending_approval")
        if not pending:
            return state

        record = await self._approval_manager.enqueue(run_id, pending)
        updated_pending = pending.model_copy(update={"approval_id": str(record.id)})
        state = {**state, "pending_approval": updated_pending, "status": "awaiting_approval"}
        await self._state_manager.save_checkpoint(
            run_id, state, step="awaiting_approval", approval_id=record.id
        )
        return state

    async def _persist_run(
        self, run_id: uuid.UUID, state: AgentGraphState, *, checkpoint_step: str
    ) -> None:
        for result in state.get("tool_results") or []:
            await self._state_manager.record_tool_call(run_id, result)

        if state.get("final_response"):
            await self._state_manager.append_message(
                run_id, "assistant", state["final_response"]
            )

        await self._state_manager.persist_graph_state(
            str(run_id), state, checkpoint_step=checkpoint_step
        )
